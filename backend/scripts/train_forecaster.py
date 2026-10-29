import argparse
import os
import joblib
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error


def build_forecasting_dataset(df: pd.DataFrame):
    """Builds features and target for Layer 2 next-hour forecasting.

    Features (5 simple, viva-explainable features per plan.md §7.1):
    1. hour_of_day (0-23)
    2. day_of_week (0-6)
    3. y_t (current ED arrivals)
    4. y_t_minus_1 (ED arrivals 1h ago)
    5. y_t_minus_24 (ED arrivals 24h ago)

    Target:
    y_next (ED arrivals 1h ahead, i.e. y_t+1)
    """
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    df["hour_of_day"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.day_of_week

    # Lags of ED arrivals
    df["y_t"] = df["ed_arrivals"]
    df["y_t_minus_1"] = df["ed_arrivals"].shift(1)
    df["y_t_minus_24"] = df["ed_arrivals"].shift(24)

    # Target: next hour ED arrivals
    df["y_next"] = df["ed_arrivals"].shift(-1)

    # Drop rows with NaN from shifting (first 24 rows and last row)
    clean_df = df.dropna(subset=["hour_of_day", "day_of_week", "y_t", "y_t_minus_1", "y_t_minus_24", "y_next"]).copy()

    feature_cols = ["hour_of_day", "day_of_week", "y_t", "y_t_minus_1", "y_t_minus_24"]
    X = clean_df[feature_cols]
    y = clean_df["y_next"]

    return X, y


def train_forecaster(data_path: str, model_output_path: str):
    print(f"Loading data from '{data_path}'...")
    df = pd.read_csv(data_path)

    X, y = build_forecasting_dataset(df)
    total_samples = len(X)

    # 80/20 temporal split (no future data leakage)
    split_idx = int(total_samples * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    print(f"Training on {len(X_train)} samples, testing on {len(X_test)} samples...")

    # HistGradientBoostingRegressor with fixed random state
    model = HistGradientBoostingRegressor(random_state=42, max_iter=100)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = root_mean_squared_error(y_test, preds)

    print(f"Test MAE: {mae:.2f} arrivals (proposed target: < 5.0)")
    print(f"Test RMSE: {rmse:.2f} arrivals")

    # Ensure parent output directory exists
    os.makedirs(os.path.dirname(model_output_path), exist_ok=True)
    joblib.dump(model, model_output_path)
    print(f"Serialized model successfully saved to '{model_output_path}'.")

    return model, mae, rmse


def main():
    parser = argparse.ArgumentParser(description="Train Layer 2 next-hour ED arrivals forecaster.")
    parser.add_argument("--data", type=str, default="hospital_operations_synthetic.csv", help="Input CSV data path.")
    parser.add_argument(
        "--model-output",
        type=str,
        default="backend/models/ed_forecaster.joblib",
        help="Path where serialized model is saved.",
    )
    args = parser.parse_args()

    train_forecaster(args.data, args.model_output)


if __name__ == "__main__":
    main()
