import argparse
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd


def generate_synthetic_data(days: int = 30, seed: int = 42) -> pd.DataFrame:
    """Generates deterministic, realistic hospital operational hourly time-series data.

    Follows the 7-field operational schema:
    - timestamp (UTC ISO format)
    - ed_arrivals (hourly arrivals with diurnal cycle and occasional surges)
    - ed_patients (active patients in ED)
    - available_beds (available inpatient beds)
    - icu_occupancy_pct (ICU occupancy percentage)
    - nurses_available (ED-assigned nurses on duty)
    - doctors_available (ED-assigned doctors on duty)
    """
    np.random.seed(seed)
    total_hours = days * 24

    # Fixed start time for reproducibility
    start_time = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
    timestamps = [start_time + timedelta(hours=i) for i in range(total_hours)]

    records = []

    for i, ts in enumerate(timestamps):
        hour = ts.hour
        day_of_week = ts.weekday()  # 0=Monday, 6=Sunday

        # Base diurnal cycle: lowest at 04:00 (~20), peak at 14:00 (~55)
        diurnal_factor = np.sin((hour - 8) * np.pi / 12)  # ranges -1 to 1
        base_arrivals = 38 + 16 * diurnal_factor

        # Weekend effect: slightly elevated Sunday/Monday
        day_factor = 1.1 if day_of_week in [0, 6] else 1.0

        # Random variation
        noise = np.random.normal(0, 3.5)
        raw_arrivals = base_arrivals * day_factor + noise

        # Inject occasional surges (roughly once every 4-5 days)
        if i in [110, 242, 386, 520, 650]:
            raw_arrivals += np.random.uniform(20, 30)

        # Inject occasional drops (e.g. severe blizzard / travel halt)
        if i in [180, 430]:
            raw_arrivals -= np.random.uniform(18, 24)

        ed_arrivals = max(5, int(round(raw_arrivals)))

        # ED active patients: tracks arrivals with some inertia
        base_patients = int(round(ed_arrivals * 0.85 + np.random.normal(0, 3)))
        ed_patients = max(8, base_patients)

        # Available beds (e.g., out of nominal 100 buffer beds; lower when ED is busy)
        bed_variation = int(round(55 - (ed_patients * 0.3) + np.random.normal(0, 4)))
        available_beds = max(10, min(95, bed_variation))

        # ICU occupancy % (baseline around 82%, fluctuating between 65% and 96%)
        icu_base = 82.0 + (ed_patients * 0.08) + np.random.normal(0, 2.5)
        icu_occupancy_pct = round(max(50.0, min(98.0, icu_base)), 1)

        # Nurses available on duty in ED: planned around baseline ~10, plus/minus shift changes
        nurse_base = max(6, int(round(ed_patients / 4.0 + np.random.choice([-1, 0, 1]))))
        nurses_available = nurse_base

        # Doctors available on duty in ED: planned around baseline ~4
        doctor_base = max(2, int(round(ed_patients / 12.0 + np.random.choice([0, 1]))))
        doctors_available = doctor_base

        records.append({
            "timestamp": ts.isoformat(),
            "ed_arrivals": ed_arrivals,
            "ed_patients": ed_patients,
            "available_beds": available_beds,
            "icu_occupancy_pct": icu_occupancy_pct,
            "nurses_available": nurses_available,
            "doctors_available": doctors_available,
        })

    df = pd.DataFrame(records)
    return df


def generate_surge_demo_data(days: int = 14, seed: int = 42) -> pd.DataFrame:
    """Generates synthetic data with a critical surge and capacity deficit in the latest hours.

    Designed for demonstration:
    - Layer 1: High patient-to-staff ratio, low beds (< 50), high ICU occupancy (>= 88%)
    - Layer 2: Elevated next-hour arrival forecast
    - Layer 3: CRITICAL_SURGE anomaly (deviation >= +30% above historical baseline)
    - Layer 4: REC-001 (nurse redeployment capped at 4) and REC-002 (bed & ICU alert)
    """
    df = generate_synthetic_data(days=days, seed=seed).copy()

    surge_hours = 6
    if len(df) > surge_hours:
        for idx in range(len(df) - surge_hours, len(df)):
            df.loc[idx, "ed_arrivals"] = int(df.loc[idx, "ed_arrivals"] + 30)
            df.loc[idx, "ed_patients"] = int(df.loc[idx, "ed_patients"] + 25)
            df.loc[idx, "available_beds"] = max(15, min(42, int(df.loc[idx, "available_beds"]) - 20))
            df.loc[idx, "icu_occupancy_pct"] = round(min(96.5, max(89.5, float(df.loc[idx, "icu_occupancy_pct"]) + 8.0)), 1)
            df.loc[idx, "nurses_available"] = min(9, int(df.loc[idx, "nurses_available"]))
            df.loc[idx, "doctors_available"] = max(3, int(df.loc[idx, "doctors_available"]))

    return df


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic hospital operations CSV data.")
    parser.add_argument("--days", type=int, default=30, help="Number of operational days to generate (default: 30).")
    parser.add_argument("--output", type=str, default="hospital_operations_synthetic.csv", help="Output CSV path for baseline dataset.")
    parser.add_argument("--surge-output", type=str, default="surge_demo.csv", help="Output CSV path for surge demo dataset (default: surge_demo.csv).")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    args = parser.parse_args()

    df = generate_synthetic_data(days=args.days, seed=args.seed)
    df.to_csv(args.output, index=False)
    print(f"Generated {len(df)} operational records ({args.days} days) saved to '{args.output}'.")

    if args.surge_output:
        df_surge = generate_surge_demo_data(days=min(args.days, 14), seed=args.seed)
        df_surge.to_csv(args.surge_output, index=False)
        print(f"Generated {len(df_surge)} surge demo records saved to '{args.surge_output}'.")


if __name__ == "__main__":
    main()
