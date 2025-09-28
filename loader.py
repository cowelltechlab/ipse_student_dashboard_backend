import os
from pathlib import Path
from dotenv import load_dotenv

def load_config():
    # Default to "dev" if APP_ENV is not set
    env = os.getenv("APP_ENV", "dev").lower()
    env_file = Path(f".env.{env}")

    if not env_file.exists():
        raise FileNotFoundError(f"Config file {env_file} not found.")

    load_dotenv(env_file)

# Load all environment variables on startup
load_config()