"""
Bulk-scores 30 sample transactions from creditcard.csv against the local
FraudGuard API so that GET /api/v1/drift?sample_size=30 has enough scored
transactions to build and persist its reference cache.

Easiest usage — just log in with an existing account (this is now the
default path, no manual token copying needed):
    python seed_transactions.py --email demo@fraudguard.ai --password DemoPass123

Still supported — pass a token directly (e.g. one you already copied from
browser DevTools, or generated some other way):
    python seed_transactions.py --token PASTE_ACCESS_TOKEN_HERE

Or set either as an env var:
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


def login(email: str, password: str) -> str:
    resp = requests.post(f"{API_BASE}/auth/login", json={"email": email, "password": password}, timeout=10)
    if resp.status_code != 200:
        print(f"ERROR: login failed for {email} ({resp.status_code}): {resp.text[:200]}")
        sys.exit(1)
    token = resp.json().get("access_token")
    if not token:
        print(f"ERROR: login succeeded but no access_token in response: {resp.text[:200]}")
        sys.exit(1)
    print(f"Logged in as {email}.")
    return token


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
    parser.add_argument("--email", default=os.environ.get("FRAUDGUARD_EMAIL"))
    parser.add_argument("--password", default=os.environ.get("FRAUDGUARD_PASSWORD"))
    parser.add_argument("--rows", type=int, default=NUM_ROWS)
    parser.add_argument("--csv", default=CSV_PATH)
    args = parser.parse_args()

    if args.token:
        token = args.token
    elif args.email and args.password:
        token = login(args.email, args.password)
    else:
        print(
            "ERROR: no way to authenticate. Either provide --email and --password "
            "(easiest — logs in for you), or --token if you already have one. "
            "FRAUDGUARD_EMAIL/FRAUDGUARD_PASSWORD/FRAUDGUARD_TOKEN env vars work too."
        )
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
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
