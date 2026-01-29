from dataclasses import dataclass
from app.core.config import settings


@dataclass(frozen=True)
class WiseEndpoints:
    profiles: str = "/v1/profiles"
    balance_accounts: str = "/v4/profiles/{profile_id}/balance-accounts"
    balances: str = "/v4/balance-accounts/{balance_account_id}/balances"
    transactions: str = "/v1/statement.json"
    webhooks: str = "/v2/subscriptions"
    transfers: str = "/v1/transfers"
    batch_groups: str = "/v1/batch-groups"
    batch_payments: str = "/v1/batch-groups/{batch_id}/payments"
    batch_funding: str = "/v1/batch-groups/{batch_id}/fund"


def base_url(environment: str) -> str:
    if environment == "production":
        return settings.wise_api_base_production.rstrip("/")
    return settings.wise_api_base_sandbox.rstrip("/")


def oauth_base_url(environment: str) -> str:
    if environment == "production":
        return settings.wise_oauth_base.rstrip("/")
    return settings.wise_oauth_base_sandbox.rstrip("/")
