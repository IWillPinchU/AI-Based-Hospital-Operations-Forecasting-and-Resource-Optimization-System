"""Simulates a live hospital feed by posting one new hourly record at a time."""
import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

TIMEOUT_SECONDS = 10
INT_FIELDS = ["ed_arrivals", "ed_patients", "available_beds", "nurses_available", "doctors_available"]


def parse_timestamp(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def hour_of_week(dt: datetime) -> int:
    return dt.weekday() * 24 + dt.hour


def build_next_record(latest_ts: datetime, source_rows: list) -> dict:
    """Next hour's record: same hour-of-week values copied from the source rows."""
    next_ts = latest_ts + timedelta(hours=1)
    target = hour_of_week(next_ts)
    for row in source_rows:
        if hour_of_week(parse_timestamp(row["timestamp"])) == target:
            record = {"timestamp": next_ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
            for field in INT_FIELDS:
                record[field] = int(row[field])
            record["icu_occupancy_pct"] = float(row["icu_occupancy_pct"])
            return record
    raise ValueError(f"No source row matches hour-of-week {target} (needed for {next_ts.isoformat()}).")


def load_source(path: str) -> list:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def http_json(url: str, payload=None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8"))


def error_detail(exc: urllib.error.HTTPError) -> str:
    try:
        return str(json.loads(exc.read().decode("utf-8")).get("detail", ""))
    except (ValueError, AttributeError):
        return ""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Simulate a live hospital data feed.")
    parser.add_argument("--api-base", default="http://localhost:8000")
    parser.add_argument("--source", default="hospital_operations_synthetic.csv")
    parser.add_argument("--interval", type=float, default=5)
    parser.add_argument("--count", type=int, default=24)
    args = parser.parse_args(argv)
    base = args.api_base.rstrip("/")

    try:
        source_rows = load_source(args.source)
    except OSError as exc:
        print(f"Cannot read source CSV '{args.source}': {exc}", file=sys.stderr)
        return 1

    for i in range(args.count):
        try:
            try:
                state = http_json(f"{base}/api/v1/current-state")
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    print("No data in the database. Upload a CSV first.", file=sys.stderr)
                else:
                    print(f"current-state failed: HTTP {exc.code} {error_detail(exc)}", file=sys.stderr)
                return 1
            record = build_next_record(parse_timestamp(state["timestamp"]), source_rows)
            try:
                result = http_json(f"{base}/api/v1/ingest/record", record)
            except urllib.error.HTTPError as exc:
                print(f"Ingest failed: HTTP {exc.code} {error_detail(exc)}", file=sys.stderr)
                return 1
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except (urllib.error.URLError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            print(f"Cannot reach the backend at {base}: {reason}", file=sys.stderr)
            return 1

        print(f"{record['timestamp']} {result.get('action')}")
        if i < args.count - 1:
            time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())
