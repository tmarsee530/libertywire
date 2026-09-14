#!/usr/bin/env python3
import os
import requests

api_key = os.environ.get("KIT_API_KEY", "").strip()
if not api_key:
    raise SystemExit("KIT_API_KEY is not available to this workflow.")

response = requests.get(
    "https://api.kit.com/v4/account",
    headers={"X-Kit-Api-Key": api_key},
    timeout=30,
)
if response.status_code != 200:
    raise SystemExit(f"Kit account validation failed with HTTP {response.status_code}.")

account = (response.json() or {}).get("account") or {}
print(f"Kit connection verified for account: {account.get('name') or account.get('id') or 'connected account'}")
