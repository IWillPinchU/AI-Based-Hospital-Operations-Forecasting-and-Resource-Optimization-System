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


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic hospital operations CSV data.")
    parser.add_argument("--days", type=int, default=30, help="Number of operational days to generate (default: 30).")
    parser.add_argument("--output", type=str, default="hospital_operations_synthetic.csv", help="Output CSV path.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    args = parser.parse_args()

    df = generate_synthetic_data(days=args.days, seed=args.seed)
    df.to_csv(args.output, index=False)
    print(f"Generated {len(df)} operational records ({args.days} days) saved to '{args.output}'.")


if __name__ == "__main__":
    main()
