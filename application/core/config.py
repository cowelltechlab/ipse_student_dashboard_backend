from functools import lru_cache
import os
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from application.core.secret_manager import SecretManager


class Settings(BaseSettings):
    project_name: str = "ipse_dashboard"
    key_vault_name: str = "cowell-tech-lab-secrets"
    load_dotenv()
    
    db_url: str = os.getenv("DB_URL")
    # db_url: str = None
    # api_key: str = None
    jwt_secret: Optional[str] = None

    class Config:
        env_file = ".env"

    def load_from_vault(self):
        sm = SecretManager(self.key_vault_name)
        # self.db_url = sm.get_secret("db-url")
        # self.api_key = sm.get_secret("api-key")
        self.jwt_secret = sm.get_secret("jwt-secret")


@lru_cache()
def get_settings():
    settings = Settings()
    settings.load_from_vault()
    return settings
