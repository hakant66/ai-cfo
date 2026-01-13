from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AI CFO"
    environment: str = "development"
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/aicfo"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60 * 24
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000"
    settlement_lag_days: int = 2

    class Config:
        env_file = ".env"


settings = Settings()
