"""
Bulk-scores 30 sample transactions from creditcard.csv against the local
FraudGuard API so that GET /api/v1/drift?sample_size=30 has enough scored
transactions to build and persist its reference cache.

Usage (run from C:\\Drishti\\FraudGuard, backend must be running):
    python seed_transactions.py --token PASTE_ACCESS_TOKEN_HERE

Or set the token as an env var:
    set FRAUDGUARD_TOKEN=eyJ...
    python seed_transactions.py
"""

import argparse
import csv
import os
import sys
import time

import requests

API_BASE = "http://127.0.0.1:8000/api/v1"
CSV_PATH = "creditcard.csv"
NUM_ROWS = 30


def build_payload(row: dict) -> dict:
    v_features = {f"V{i}": float(row[f"V{i}"]) for i in range(1, 29)}
    return {
        "time_feature": float(row["Time"]),
        "amount": float(row["Amount"]),
        "v_features": v_features,
        "currency": "INR",
        "merchant": "Seed Script",
        "customer_reference": "seed-demo",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", default=os.environ.get("FRAUDGUARD_TOKEN"))
    parser.add_argument("--rows", type=int, default=NUM_ROWS)
    parser.add_argument("--csv", default=CSV_PATH)
    args = parser.parse_args()

    if not args.token:
        print("ERROR: no access token provided. Use --token or set FRAUDGUARD_TOKEN.")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {args.token}",
        "Content-Type": "application/json",
    }

    ok, failed = 0, 0
    with open(args.csv, newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= args.rows:
                break
            payload = build_payload(row)
            resp = requests.post(f"{API_BASE}/predict", headers=headers, json=payload, timeout=10)
            if resp.status_code == 201:
                ok += 1
                print(f"[{i+1}/{args.rows}] scored OK")
            else:
                failed += 1
                print(f"[{i+1}/{args.rows}] FAILED ({resp.status_code}): {resp.text[:200]}")
            time.sleep(0.05)

    print(f"\nDone. {ok} scored, {failed} failed.")
    if ok >= 30:
        print("You should now have enough scored transactions for /drift to build its reference cache.")


if __name__ == "__main__":
    main()
