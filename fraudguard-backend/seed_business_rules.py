"""
Seeds a FraudGuard deployment with a realistic starter set of business
rules — via the real POST /rules endpoint (not a direct database write), so
it works against ANY deployment (local or a live Render/Vercel one) just by
changing --base-url, with no database credentials needed at all.

Requires an ADMIN account (rule creation is admin-only — see
app/api/v1/rules.py's require_role). Pass credentials for one you already
have; this script does not create accounts.

Idempotent: skips any rule whose `name` already exists on that deployment
(checked via GET /rules first), so it's safe to re-run.

Uses only the Python standard library (urllib) — no `pip install` required.

Usage:
    python seed_business_rules.py --email raghva@gmail.com --password Raj@1115
    python seed_business_rules.py --base-url https://fraud-guard-s4jt.onrender.com/api/v1 --email raghva@gmail.com --password Raj@1115
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

RULES = [
    {
        "name": "Block very large first-time transactions",
        "field": "amount",
        "operator": "gt",
        "value": "50000",
        "action": "block",
    },
    {
        "name": "Flag high-value transactions",
        "field": "amount",
        "operator": "gt",
        "value": "20000",
        "action": "flag",
    },
    {
        "name": "Notify on foreign currency",
        "field": "currency",
        "operator": "neq",
        "value": "INR",
        "action": "notify",
    },
    {
        "name": "Block known high-risk merchant category",
        "field": "merchant",
        "operator": "contains",
        "value": "Crypto",
        "action": "block",
    },
    {
        "name": "Flag suspicious IP pattern",
        "field": "ip_address",
        "operator": "contains",
        "value": "0.0.0.0",
        "action": "flag",
    },
    {
        "name": "Flag odd-hour transactions",
        "field": "time_feature",
        "operator": "gt",
        "value": "144000",
        "action": "flag",
    },
    {
        # Note: NOT "device_info eq ''" for missing device info — while
        # rule_engine.py's own matching logic does treat a None field as ""
        # internally (so that design intent is real), RuleCreate's schema
        # requires value to be non-empty (min_length=1), so an empty-string
        # rule can never actually be saved through the API. This is a
        # genuine small gap between the engine and the endpoint, not
        # something to work around with a fake value — substituting a
        # concretely useful rule instead.
        "name": "Notify on premium ticketing/entertainment merchants",
        "field": "merchant",
        "operator": "contains",
        "value": "BookMyShow",
        "action": "notify",
    },
]


def _request(base_url: str, method: str, path: str, body: dict = None, token: str = None) -> tuple[int, dict]:
    url = f"{base_url}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def login(base_url: str, email: str, password: str) -> str:
    status, body = _request(base_url, "POST", "/auth/login", {"email": email, "password": password})
    if status != 200:
        print(f"ERROR: login failed for {email} ({status}): {body}", file=sys.stderr)
        sys.exit(1)
    if body.get("user", {}).get("role") != "admin":
        print(f"ERROR: {email} is role={body.get('user', {}).get('role')!r}, but creating rules requires admin.", file=sys.stderr)
        sys.exit(1)
    print(f"Logged in as {email} (admin).")
    return body["access_token"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed FraudGuard with starter business rules via the real API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1", help="API base URL")
    parser.add_argument("--email", required=True, help="Admin account email")
    parser.add_argument("--password", required=True, help="Admin account password")
    args = parser.parse_args()

    token = login(args.base_url, args.email, args.password)

    status, body = _request(args.base_url, "GET", "/rules", token=token)
    if status != 200:
        print(f"ERROR: could not list existing rules ({status}): {body}", file=sys.stderr)
        sys.exit(1)
    existing_names = {r["name"] for r in body.get("items", [])}

    created, skipped, failed = 0, 0, 0
    for spec in RULES:
        if spec["name"] in existing_names:
            print(f"Skipping (already exists): {spec['name']}")
            skipped += 1
            continue
        status, body = _request(args.base_url, "POST", "/rules", spec, token=token)
        if status == 201:
            print(f"Created: {spec['name']} ({spec['field']} {spec['operator']} {spec['value']!r} -> {spec['action']})")
            created += 1
        else:
            print(f"FAILED: {spec['name']} ({status}): {body}", file=sys.stderr)
            failed += 1

    print(f"\nDone. {created} created, {skipped} skipped (already present), {failed} failed.")


if __name__ == "__main__":
    main()
