import time
import requests
from datetime import datetime, timedelta, timezone
from typing import Any
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.wise_encryption import wise_decrypt, wise_encrypt
from app.models.models import IntegrationCredentialWise, WiseSettings
from app.connectors.wise.config import base_url, oauth_base_url


class WiseApiError(RuntimeError):
    pass


class WiseApiClient:
    def __init__(self, db: Session, company_id: int, environment: str):
        self.db = db
        self.company_id = company_id
        self.environment = environment

    def _credentials(self) -> IntegrationCredentialWise:
        creds = self.db.query(IntegrationCredentialWise).filter(
            IntegrationCredentialWise.company_id == self.company_id,
            IntegrationCredentialWise.wise_environment == self.environment,
        ).first()
        if not creds:
            raise WiseApiError("Wise credentials not found")
        return creds

    def _get_access_token(self, creds: IntegrationCredentialWise) -> str:
        return wise_decrypt(creds.oauth_access_token_encrypted)

    def _refresh(self, creds: IntegrationCredentialWise) -> None:
        payload = {
            "grant_type": "refresh_token",
            "client_id": self._client_id(),
            "client_secret": self._client_secret(),
            "refresh_token": wise_decrypt(creds.oauth_refresh_token_encrypted),
        }
        response = requests.post(
            f"{oauth_base_url(self.environment)}/oauth/token",
            data=payload,
            timeout=30,
        )
        if response.status_code >= 400:
            raise WiseApiError(f"Token refresh failed: {response.text}")
        data = response.json()
        creds.oauth_access_token_encrypted = wise_encrypt(data["access_token"])
        if data.get("refresh_token"):
            creds.oauth_refresh_token_encrypted = wise_encrypt(data["refresh_token"])
        expires_in = int(data.get("expires_in") or 0)
        if expires_in:
            creds.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        creds.updated_at = datetime.now(timezone.utc)
        self.db.commit()

    def request(self, method: str, path: str, params: dict[str, Any] | None = None, json: Any | None = None) -> Any:
        creds = None
        api_token = self._api_token()
        if not api_token:
            creds = self._credentials()
            if creds.token_expires_at and creds.token_expires_at <= datetime.now(timezone.utc) + timedelta(minutes=2):
                self._refresh(creds)
        url = f"{base_url(self.environment)}{path}"
        token = api_token or self._get_access_token(creds)
        refreshed = False
        for attempt in range(3):
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.request(method, url, params=params, json=json, headers=headers, timeout=30)
            if response.status_code == 401 and not refreshed:
                if creds:
                    self._refresh(creds)
                    token = self._get_access_token(creds)
                    refreshed = True
                    continue
            if response.status_code in {429, 500, 502, 503} and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            if response.status_code >= 400:
                raise WiseApiError(f"Wise API error {response.status_code}: {response.text}")
            if response.text:
                return response.json()
            return {}
        raise WiseApiError("Wise API request failed after retries")

    def _client_id(self) -> str:
        settings_row = self.db.query(WiseSettings).filter(
            WiseSettings.company_id == self.company_id,
            WiseSettings.wise_environment == self.environment,
        ).first()
        if settings_row and settings_row.wise_client_id:
            return settings_row.wise_client_id
        return settings.wise_client_id

    def _client_secret(self) -> str:
        settings_row = self.db.query(WiseSettings).filter(
            WiseSettings.company_id == self.company_id,
            WiseSettings.wise_environment == self.environment,
        ).first()
        if settings_row and settings_row.wise_client_secret_encrypted:
            return wise_decrypt(settings_row.wise_client_secret_encrypted)
        return settings.wise_client_secret

    def _api_token(self) -> str | None:
        settings_row = self.db.query(WiseSettings).filter(
            WiseSettings.company_id == self.company_id,
            WiseSettings.wise_environment == self.environment,
        ).first()
        if settings_row and settings_row.wise_api_token_encrypted:
            return wise_decrypt(settings_row.wise_api_token_encrypted)
        if settings.wise_api_token:
            return settings.wise_api_token
        return None


def exchange_oauth_code(environment: str, code: str, redirect_uri: str, client_id: str, client_secret: str) -> dict[str, Any]:
    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }
    response = requests.post(
        f"{oauth_base_url(environment)}/oauth/token",
        data=payload,
        timeout=30,
    )
    if response.status_code >= 400:
        raise WiseApiError(f"OAuth exchange failed: {response.text}")
    return response.json()
