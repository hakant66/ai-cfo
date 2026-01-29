from pydantic import BaseModel


class WiseSettingsOut(BaseModel):
    wise_client_id: str | None
    wise_environment: str
    has_client_secret: bool
    has_webhook_secret: bool
    has_api_token: bool


class WiseSettingsUpdate(BaseModel):
    wise_client_id: str | None = None
    wise_client_secret: str | None = None
    wise_environment: str | None = None
    webhook_secret: str | None = None
    wise_api_token: str | None = None
    auth_mode: str | None = None
