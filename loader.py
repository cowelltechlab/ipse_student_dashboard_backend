import os
from pathlib import Path
from dotenv import load_dotenv

def load_config():
    # 1) Load base .env first (doesn't override anything already set by the OS)
    load_dotenv(".env", override=False)

    # 2) Read APP_ENV (now present if it was only in .env)
    env = os.getenv("APP_ENV", "dev").lower()
    env_path = Path(f".env.{env}")
    if not env_path.exists():
        raise FileNotFoundError(f"Config file {env_path} not found.")

    # 3) Load the env-specific file and LET IT OVERRIDE base/OS if needed
    load_dotenv(env_path, override=True)

    # # 4) Optional hardening: normalize and validate critical URLs
    # fb = os.getenv("FRONTEND_BASE_URL", "").strip().strip('"').strip("'")
    # if not fb or "localhost" in fb:
    #     raise RuntimeError(f"FRONTEND_BASE_URL misconfigured: {fb!r}")
