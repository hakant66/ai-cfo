from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    app_name: str = "ai-cfo"
    environment: str = "local"
    database_url: str
    redis_url: str = "redis://redis:6379/0"
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    document_storage_path: str = "storage/documents"
    shopify_url: str = ""
    shopify_access_token: str = ""
    shopify_use_graphql: bool = False
    wise_client_id: str = ""
    wise_client_secret: str = ""
    wise_redirect_uri: str = ""
    wise_oauth_scopes_read: str = "profile balance transactions"
    wise_oauth_scopes_write: str = ""
    wise_write_enabled: bool = False
    wise_api_base_sandbox: str = "https://api.sandbox.transferwise.tech"
    wise_api_base_production: str = "https://api.transferwise.com"
    wise_oauth_base: str = "https://api.transferwise.com"
    wise_oauth_base_sandbox: str = "https://api.sandbox.transferwise.tech"
    wise_webhook_secret: str = ""
    wise_webhook_url: str = ""
    encryption_key: str = ""
    primary_company_id: int | None = None
    wise_public_key: str = ""
    wise_private_key: str = ""
    wise_api_token: str = ""
    stripe_api_base: str = "http://stripe-api:8002"
    dify_external_kb_api_key: str = ""

    @field_validator("primary_company_id", mode="before")
    @classmethod
    def _empty_primary_company(cls, value):
        if value in ("", None):
            return None
        return value

    @field_validator("wise_public_key", "wise_private_key", mode="before")
    @classmethod
    def _empty_wise_keys(cls, value):
        if value in ("", None):
            return ""
        return value

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
