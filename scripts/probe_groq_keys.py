"""Probe each Groq key in GROQ_API_KEYS with a 1-token request to check quota state."""
from __future__ import annotations

import hashlib
import os
import sys
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

raw = os.getenv("GROQ_API_KEYS", os.getenv("GROQ_API_KEY", ""))
keys = [k.strip() for k in raw.split(",") if k.strip()]
if not keys:
    print("No keys found in GROQ_API_KEYS / GROQ_API_KEY")
    sys.exit(1)

URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

def kid(k: str) -> str:
    return "k" + hashlib.sha256(k.encode()).hexdigest()[:8]

print(f"Probing {len(keys)} key(s) against model={MODEL}\n")

for k in keys:
    headers = {"Authorization": f"Bearer {k}", "Content-Type": "application/json"}
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
        "temperature": 0,
    }
    t0 = time.time()
    try:
        r = httpx.post(URL, headers=headers, json=body, timeout=15.0)
        dt = (time.time() - t0) * 1000
        status = r.status_code
        # Headers Groq sends back about rate limits
        rl = {h: r.headers.get(h) for h in [
            "x-ratelimit-limit-requests",
            "x-ratelimit-remaining-requests",
            "x-ratelimit-reset-requests",
            "x-ratelimit-limit-tokens",
            "x-ratelimit-remaining-tokens",
            "x-ratelimit-reset-tokens",
            "retry-after",
        ] if r.headers.get(h)}
        print(f"[{kid(k)}] HTTP {status} in {dt:.0f}ms")
        if rl:
            for h, v in rl.items():
                print(f"    {h}: {v}")
        if status >= 400:
            try:
                err = r.json().get("error", {})
                msg = err.get("message", "")
                code = err.get("code", "")
                print(f"    error.code: {code}")
                print(f"    error.message: {msg[:300]}")
            except Exception:
                print(f"    body: {r.text[:300]}")
        print()
    except Exception as e:
        print(f"[{kid(k)}] EXCEPTION: {type(e).__name__}: {e}\n")
