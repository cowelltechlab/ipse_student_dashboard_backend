from pydantic import BaseSettings
from functools import lru_cache
from application.core.secret_manager import SecretManager


class Settings(BaseSettings):
    project_name: str = "ipse_dashboard"
    key_vault_name: str = "my-azure-keyvault"
    db_url: str = (
        "Driver={ODBC Driver 18 for SQL Server};"
        "Server=tcp:ai-for-higher-learning.database.windows.net,1433;"
        "Database=ai-for-higher-learning;"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Authentication=ActiveDirectoryAzureCLI;"
    )
    # db_url: str = None
    api_key: str = None

    class Config:
        env_file = ".env"

    def load_from_vault(self):
        sm = SecretManager(self.key_vault_name)
        # self.db_url = sm.get_secret("db-url")
        self.api_key = sm.get_secret("api-key")


@lru_cache()
def get_settings():
    settings = Settings()
    settings.load_from_vault()
    return settings
