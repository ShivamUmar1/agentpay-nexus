import os
import json
import httpx
import time
from dotenv import load_dotenv

load_dotenv("D:/paypal hackathon/.env", override=True)
api_key = os.getenv("GEMINI_API_KEY", "").strip()

print("=== BENCHMARKING GEMINI MODELS ===")

candidates = [
    "gemini-flash-latest",
    "gemini-3-flash-preview",
    "gemini-2.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-pro-latest"
]

for model in candidates:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": "Reply with 'PONG' only."}]}]
    }
    t0 = time.time()
    try:
        with httpx.Client(timeout=20.0) as client:
            res = client.post(url, json=payload)
            lat = round((time.time() - t0) * 1000, 1)
            print(f"{model}: HTTP {res.status_code} ({lat}ms)")
            if res.status_code == 200:
                text = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                print(f"  Response: {text}")
            else:
                print(f"  Error: {res.text[:150]}")
    except Exception as e:
        print(f"  Exception on {model}: {e}")
