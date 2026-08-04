"""
Seeds a FraudGuard deployment with realistic demo data for a live
presentation — registers (or logs into) a demo account, then submits a
varied batch of transactions through the REAL `/predict` pipeline (not
direct DB inserts) so every downstream artifact is genuinely consistent:
FraudLog entries, notifications, SHAP explanations, and dashboard stats all
reflect transactions that actually went through scoring, exactly like a real
user's would.

Uses only the Python standard library (urllib) deliberately — no `pip
install` required before a demo, when you have the least appetite for
debugging a fresh dependency issue.

Usage:
    python seed_demo_data.py
    python seed_demo_data.py --base-url https://fraud-guard-s4jt.onrender.com/api/v1
    python seed_demo_data.py --base-url http://127.0.0.1:8000/api/v1 --count 40

Safe to re-run: submitting more transactions never deletes or resets
anything, it only adds more.
"""

import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.request

DEMO_EMAIL = "demo@fraudguard.ai"
DEMO_PASSWORD = "DemoPass123"
DEMO_NAME = "Demo Analyst"

MERCHANTS = [
    "Amazon India", "Swiggy", "Zomato", "BigBasket", "Flipkart",
    "IRCTC", "Reliance Digital", "Croma", "Uber", "Ola",
    "Starbucks India", "Apollo Pharmacy", "Myntra", "BookMyShow", "Airtel",
]
CURRENCIES = ["INR", "INR", "INR", "USD", "EUR"]  # weighted toward INR


def _request(base_url: str, method: str, path: str, body: dict = None, token: str = None) -> tuple[int, dict]:
    url = f"{base_url}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def get_demo_token(base_url: str) -> str:
    """Logs in as the demo account, registering it first if it doesn't exist yet."""
    status, body = _request(base_url, "POST", "/auth/login", {"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    if status == 200:
        print(f"Logged in as existing demo account ({DEMO_EMAIL}).")
        return body["access_token"]

    print(f"Demo account doesn't exist yet — registering {DEMO_EMAIL} ...")
    status, body = _request(
        base_url, "POST", "/auth/register",
        {"email": DEMO_EMAIL, "password": DEMO_PASSWORD, "full_name": DEMO_NAME},
    )
    if status != 201:
        print(f"Registration failed ({status}): {body}", file=sys.stderr)
        sys.exit(1)
    print(f"Registered as role={body.get('role')}.")

    status, body = _request(base_url, "POST", "/auth/login", {"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    if status != 200:
        print(f"Login after registration failed ({status}): {body}", file=sys.stderr)
        sys.exit(1)
    return body["access_token"]


# The EXACT V-feature pattern independently verified (both locally and on
# the live Render deployment) to score risk 91.59 / "blocked". Critically,
# this is a specific MIXED-SIGN pattern (V1 very negative, V2 positive, V3
# negative, V4 positive...) — not just "large numbers". An earlier version
# of this script generated each feature as independent Gaussian noise
# sharing one mean, which nudges every feature the same direction — that
# never recreates this shape, no matter how large the magnitude, and
# consistently scored near-zero risk regardless of how "extreme" the raw
# numbers looked. Scaling THIS proven pattern up/down preserves the shape
# the model actually keys off of (see its own SHAP output: V14, V4, V12,
# V10, V3 dominate) while still varying magnitude across transactions.
_FRAUD_PATTERN = {
    "V1": -20, "V2": 15, "V3": -18, "V4": 10, "V5": -12,
    "V6": 8, "V7": -15, "V8": 12, "V9": -10, "V10": -20,
    "V11": 14, "V12": -16, "V13": 5, "V14": -22, "V15": 8,
    "V16": -14, "V17": -25, "V18": -12, "V19": 10, "V20": 15,
    "V21": 12, "V22": -8, "V23": 10, "V24": -5, "V25": 6,
    "V26": -7, "V27": 15, "V28": 12,
}


def _v_features_normal(spread: float = 1.0) -> dict:
    """Independent near-zero Gaussian noise — confirmed working: this tier
    correctly scores near-0 risk on the real deployed model."""
    return {f"V{i}": round(random.gauss(0, spread), 4) for i in range(1, 29)}


def _v_features_fraud_like(scale: float, jitter: float) -> dict:
    """Scales the PROVEN fraud pattern by `scale` (0 = no signal, 1 = the
    exact profile that scored 91.59) and adds small independent `jitter`
    noise per feature so generated transactions vary without losing the
    shape the model actually responds to."""
    return {k: round(v * scale + random.gauss(0, jitter), 4) for k, v in _FRAUD_PATTERN.items()}


def build_transaction(tier: str) -> dict:
    merchant = random.choice(MERCHANTS)
    currency = random.choice(CURRENCIES)

    if tier == "normal":
        amount = round(random.uniform(5, 400), 2)
        v_features = _v_features_normal(spread=1.0)
    elif tier == "suspicious":
        amount = round(random.uniform(500, 5000), 2)
        v_features = _v_features_fraud_like(scale=random.uniform(0.25, 0.5), jitter=1.5)
    else:  # "fraudulent"
        amount = round(random.uniform(8000, 60000), 2)
        v_features = _v_features_fraud_like(scale=random.uniform(0.8, 1.3), jitter=2.0)

    return {
        "time_feature": random.randint(0, 172800),
        "amount": amount,
        "v_features": v_features,
        "currency": currency,
        "merchant": merchant,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed FraudGuard with demo transactions.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1", help="API base URL")
    parser.add_argument("--count", type=int, default=35, help="Number of transactions to submit")
    args = parser.parse_args()

    # Roughly: 60% ordinary, 25% suspicious, 15% clearly fraudulent —
    # tuned to produce a mixed, presentable dashboard rather than an even
    # split, since most real-world traffic IS legitimate.
    tiers = (
        ["normal"] * int(args.count * 0.60)
        + ["suspicious"] * int(args.count * 0.25)
        + ["fraudulent"] * int(args.count * 0.15)
    )
    random.shuffle(tiers)

    print(f"Seeding {len(tiers)} transactions against {args.base_url} ...\n")
    token = get_demo_token(args.base_url)

    tally = {"approve": 0, "mfa_required": 0, "blocked": 0, "error": 0}
    for i, tier in enumerate(tiers, start=1):
        payload = build_transaction(tier)
        status, body = _request(args.base_url, "POST", "/predict", payload, token=token)
        if status == 201:
            decision = body["prediction"]["decision"]
            risk = body["prediction"]["risk_score"]
            tally[decision] = tally.get(decision, 0) + 1
            print(f"[{i:>2}/{len(tiers)}] {tier:<11} -> {decision:<13} (risk {risk:>5.1f})  {payload['merchant']}")
        else:
            tally["error"] += 1
            print(f"[{i:>2}/{len(tiers)}] {tier:<11} -> FAILED ({status}): {body}")
        time.sleep(2.2)  # RATE_LIMIT_PREDICT = 30/minute (~1 every 2s) — stay safely under it

    print("\nDone. Decision breakdown:")
    for decision, count in tally.items():
        if count:
            print(f"  {decision}: {count}")
    print(f"\nDemo login -> email: {DEMO_EMAIL}  password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
