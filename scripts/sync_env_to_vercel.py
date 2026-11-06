import os
import subprocess
import sys
from pathlib import Path
from dotenv import dotenv_values

ENV_PATH = Path("D:/paypal hackathon/.env")

REQUIRED_VARS = [
    "DATABASE_URL",
    "GEMINI_API_KEY",
    "PAYPAL_CLIENT_ID",
    "PAYPAL_CLIENT_SECRET",
    "PAYPAL_MODE",
    "GEMINI_MODEL",
    "VITE_PAYPAL_CLIENT_ID"
]

def sync_to_vercel():
    vals = dotenv_values(ENV_PATH)
    if not vals:
        print(f"No environment variables found in {ENV_PATH}.")
        sys.exit(1)
        
    print("=== SYNCHRONIZING SECURE ENVIRONMENT VARIABLES TO VERCEL ===")
    for key in REQUIRED_VARS:
        val = vals.get(key)
        if not val:
            print(f"[SKIP] {key}: not found in .env")
            continue
            
        print(f"Syncing {key} to Vercel...")
        for env_target in ["production", "preview"]:
            cmd = [
                "cmd.exe", "/c", "npx", "vercel", "env", "add",
                key, env_target,
                "--force", "--yes", "--non-interactive",
                "--value", val
            ]
            try:
                res = subprocess.run(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    timeout=20
                )
                if res.returncode == 0:
                    print(f"  + [OK] {key} -> {env_target}")
                else:
                    err = res.stderr.strip() or res.stdout.strip()
                    print(f"  - [NOTICE] {key} -> {env_target}: {err}")
            except Exception as e:
                print(f"  - [ERROR] {key} -> {env_target}: {e}")

    print("\nEnvironment synchronization complete!")

if __name__ == "__main__":
    sync_to_vercel()
