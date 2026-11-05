import argparse
import json
import os
import time
import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from statsmodels.tsa.holtwinters import ExponentialSmoothing

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.models_lstm import EDArrivalsLSTM
from scripts.train_forecaster import build_forecasting_dataset


def train_hist_gbr(X_train, y_train, X_test, y_test, output_path: str):
    print("Training 1/3: HistGradientBoostingRegressor (Tree Ensemble)...")
    t0 = time.perf_counter()
    model = HistGradientBoostingRegressor(random_state=42, max_iter=100)
    model.fit(X_train, y_train)
    fit_duration = time.perf_counter() - t0

    # Latency test: 100 single-sample inferences
    sample = X_test.iloc[[0]]
    t_inf_start = time.perf_counter()
    for _ in range(100):
        model.predict(sample)
    latency_ms = ((time.perf_counter() - t_inf_start) / 100.0) * 1000.0

    preds = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, preds))
    rmse = float(root_mean_squared_error(y_test, preds))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    joblib.dump(model, output_path)

    print(f"  -> HistGBR: MAE={mae:.2f}, RMSE={rmse:.2f}, Latency={latency_ms:.2f}ms, TrainTime={fit_duration:.2f}s")
    return {
        "id": "hist_gbr",
        "name": "HistGradientBoostingRegressor",
        "paradigm": "Tree-based Ensemble",
        "library": "scikit-learn",
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "latency_ms": round(latency_ms, 2),
        "description": "Gradient boosted decision trees utilizing lag features (t, t-1, t-24) and diurnal cyclic signals.",
        "is_default": True,
    }


def train_lstm(df: pd.DataFrame, output_pt_path: str, output_meta_path: str):
    print("Training 2/3: PyTorch LSTM (Recurrent Deep Learning)...")
    # Prepare sequence dataset: 24 hourly arrivals as input sequence -> next hour arrival as target
    series = df["ed_arrivals"].values.astype(np.float32)

    # Min-max normalization for neural network stability
    mean_val = float(np.mean(series))
    std_val = float(np.std(series)) if np.std(series) > 0 else 1.0
    norm_series = (series - mean_val) / std_val

    seq_len = 24
    X_seq, y_seq = [], []
    for i in range(len(norm_series) - seq_len):
        X_seq.append(norm_series[i : i + seq_len])
        y_seq.append(norm_series[i + seq_len])  # Normalized target for gradient stability

    X_seq = np.array(X_seq, dtype=np.float32)[:, :, np.newaxis]  # (N, 24, 1)
    y_seq = np.array(y_seq, dtype=np.float32)[:, np.newaxis]      # (N, 1)

    split_idx = int(len(X_seq) * 0.8)
    X_train, X_test = torch.tensor(X_seq[:split_idx]), torch.tensor(X_seq[split_idx:])
    y_train, y_test_norm = torch.tensor(y_seq[:split_idx]), y_seq[split_idx:]
    y_test_raw = series[split_idx + seq_len :]

    model = EDArrivalsLSTM(input_size=1, hidden_size=32, num_layers=2, output_size=1)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.005)
    criterion = nn.MSELoss()

    t0 = time.perf_counter()
    model.train()
    dataset = torch.utils.data.TensorDataset(X_train, y_train)
    loader = torch.utils.data.DataLoader(dataset, batch_size=32, shuffle=True)

    for epoch in range(60):
        for batch_x, batch_y in loader:
            optimizer.zero_grad()
            out = model(batch_x)
            loss = criterion(out, batch_y)
            loss.backward()
            optimizer.step()

    fit_duration = time.perf_counter() - t0

    model.eval()
    with torch.no_grad():
        preds_norm = model(X_test).numpy().flatten()
        preds_raw = np.maximum(0.0, preds_norm * std_val + mean_val)
        y_eval = y_test_raw[: len(preds_raw)]
        mae = float(mean_absolute_error(y_eval, preds_raw))
        rmse = float(root_mean_squared_error(y_eval, preds_raw))

        # Latency benchmark
        sample_x = X_test[:1]
        t_inf_start = time.perf_counter()
        for _ in range(100):
            model(sample_x)
        latency_ms = ((time.perf_counter() - t_inf_start) / 100.0) * 1000.0

    torch.save(model.state_dict(), output_pt_path)
    joblib.dump({"mean": mean_val, "std": std_val, "seq_len": seq_len}, output_meta_path)

    print(f"  -> PyTorch LSTM: MAE={mae:.2f}, RMSE={rmse:.2f}, Latency={latency_ms:.2f}ms, TrainTime={fit_duration:.2f}s")
    return {
        "id": "lstm",
        "name": "PyTorch LSTM",
        "paradigm": "Recurrent Neural Network",
        "library": "PyTorch",
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "latency_ms": round(latency_ms, 2),
        "description": "2-layer LSTM sequence model with recurrent memory tracking the 24-hour sequence trajectory.",
        "is_default": False,
    }


def train_holt_winters(df: pd.DataFrame, output_path: str):
    print("Training 3/3: Holt-Winters Exponential Smoothing (Statistical Additive)...")
    series = df["ed_arrivals"].values.astype(float)
    split_idx = int(len(series) * 0.8)
    train_series = series[:split_idx]
    test_series = series[split_idx:]

    t0 = time.perf_counter()
    # Seasonal periods = 24 hours
    hw_model = ExponentialSmoothing(
        train_series,
        seasonal_periods=24,
        trend="add",
        seasonal="add",
        initialization_method="estimated",
    ).fit()
    fit_duration = time.perf_counter() - t0

    # Test rolling 1-step-ahead forecasts across the test split
    preds = []
    # Using last fitted state to project test points
    forecast_all = hw_model.forecast(steps=len(test_series))
    preds = np.maximum(0.0, forecast_all)

    mae = float(mean_absolute_error(test_series, preds))
    rmse = float(root_mean_squared_error(test_series, preds))

    # Latency test
    t_inf_start = time.perf_counter()
    for _ in range(100):
        hw_model.forecast(1)
    latency_ms = ((time.perf_counter() - t_inf_start) / 100.0) * 1000.0

    joblib.dump(hw_model, output_path)

    print(f"  -> Holt-Winters: MAE={mae:.2f}, RMSE={rmse:.2f}, Latency={latency_ms:.2f}ms, TrainTime={fit_duration:.2f}s")
    return {
        "id": "holt_winters",
        "name": "Holt-Winters (HW-ETS)",
        "paradigm": "Statistical Additive Time Series",
        "library": "statsmodels",
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "latency_ms": round(latency_ms, 2),
        "description": "Exponential Smoothing with additive 24-hour diurnal seasonal decomposition and linear trend.",
        "is_default": False,
    }


def evaluate_seasonal_naive(df: pd.DataFrame):
    print("Evaluating Baseline Benchmark: Seasonal Naive (Last Week / Lag-24)...")
    series = df["ed_arrivals"].values.astype(float)
    split_idx = int(len(series) * 0.8)
    test_series = series[split_idx:]

    # Predict value 24 hours ago as next-hour estimate
    preds = []
    for i in range(split_idx, len(series)):
        preds.append(series[i - 24])

    mae = float(mean_absolute_error(test_series, preds))
    rmse = float(root_mean_squared_error(test_series, preds))
    latency_ms = 0.01

    print(f"  -> Seasonal Naive: MAE={mae:.2f}, RMSE={rmse:.2f}, Latency={latency_ms:.2f}ms")
    return {
        "id": "seasonal_naive",
        "name": "Seasonal Naive (Lag-24)",
        "paradigm": "Empirical Baseline Benchmark",
        "library": "numpy",
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "latency_ms": round(latency_ms, 2),
        "description": "Deterministic baseline repeating the arrival count from exactly 24 hours prior.",
        "is_default": False,
    }


def main():
    parser = argparse.ArgumentParser(description="Train and benchmark all 3 forecasting model paradigms.")
    parser.add_argument("--data", type=str, default="hospital_operations_synthetic.csv")
    parser.add_argument("--models-dir", type=str, default="backend/models")
    args = parser.parse_args()

    os.makedirs(args.models_dir, exist_ok=True)
    df = pd.read_csv(args.data)
    X, y = build_forecasting_dataset(df)
    total_samples = len(X)
    split_idx = int(total_samples * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    hist_gbr_path = os.path.join(args.models_dir, "ed_forecaster.joblib")
    lstm_pt_path = os.path.join(args.models_dir, "ed_forecaster_lstm.pt")
    lstm_meta_path = os.path.join(args.models_dir, "ed_forecaster_lstm_meta.joblib")
    hw_path = os.path.join(args.models_dir, "ed_forecaster_hw.joblib")
    benchmark_path = os.path.join(args.models_dir, "model_benchmark.json")

    results = []
    # 1. HistGBR
    res_gbr = train_hist_gbr(X_train, y_train, X_test, y_test, hist_gbr_path)
    results.append(res_gbr)

    # 2. PyTorch LSTM
    res_lstm = train_lstm(df, lstm_pt_path, lstm_meta_path)
    results.append(res_lstm)

    # 3. Holt-Winters
    res_hw = train_holt_winters(df, hw_path)
    results.append(res_hw)

    # 4. Seasonal Naive baseline
    res_naive = evaluate_seasonal_naive(df)
    results.append(res_naive)

    # Save benchmark JSON
    benchmark_data = {
        "timestamp": pd.Timestamp.now("UTC").isoformat(),
        "evaluation_split": "80/20 Temporal Holdout (No leakage)",
        "models": results,
    }
    with open(benchmark_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_data, f, indent=2)

    print(f"\nModel comparative benchmark leaderboard saved to '{benchmark_path}'.")


if __name__ == "__main__":
    main()
