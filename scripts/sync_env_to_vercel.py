import os
import subprocess
import sys
from pathlib import Path

ENV_PATH = Path("D:/paypal hackathon/.env")

REQUIRED_VARS = [
    "DATABASE_URL",
    "GEMINI_API_KEY",
    "PAYPAL_CLIENT_ID",
    "PAYPAL_CLIENT_SECRET",
    "PAYPAL_MODE",
    "GEMINI_MODEL"
]

def load_local_env():
    if not ENV_PATH.exists():
        return {}
    env_vars = {}
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if v:
                    env_vars[k] = v
    return env_vars

def sync_to_vercel(env_vars):
    print("=== SYNCHRONIZING SECURE ENVIRONMENT VARIABLES TO VERCEL ===\n")
    for key, val in env_vars.items():
        if key not in REQUIRED_VARS:
            continue
        print(f"Setting {key} in Vercel Production...")
        # Use vercel env add with stdin to avoid printing secrets in terminal args
        for env_target in ["production", "preview", "development"]:
            # First remove existing to prevent duplicate errors
            cmd_rm = f"npx.cmd vercel env rm {key} {env_target} -y"
            subprocess.run(cmd_rm, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Now add
            proc = subprocess.Popen(
                f"npx.cmd vercel env add {key} {env_target}",
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = proc.communicate(input=f"{val}\n")
            if proc.returncode == 0:
                print(f"  ✓ {key} added to {env_target}")
            else:
                print(f"  Note on {key} ({env_target}): {stdout.strip() or stderr.strip()}")

    print("\nEnvironment synchronization complete!")

if __name__ == "__main__":
    env_vars = load_local_env()
    if not env_vars:
        print(f"No environment variables found in {ENV_PATH}.")
        print("Please configure your keys in .env, then re-run this script.")
        sys.exit(1)
    sync_to_vercel(env_vars)

