from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

class SecretManager:
    def __init__(self, key_vault_name):
        KVUri = f"https://{key_vault_name}.vault.azure.net"
        credential = DefaultAzureCredential()
        self.client = SecretClient(vault_url=KVUri, credential=credential)

    def get_secret(self, name):
        return self.client.get_secret(name).value
