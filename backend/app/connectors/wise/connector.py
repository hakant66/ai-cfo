from datetime import datetime, timezone
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.connectors.wise.client import WiseApiClient
from app.connectors.wise.config import WiseEndpoints
from app.models.models import (
    IntegrationCredentialWise,
    WiseProfile,
    WiseBalanceAccount,
    WiseBalance,
    WiseTransactionRaw,
    WiseWebhookSubscription,
    BankAccount,
    BankBalance,
    BankTransaction,
    WiseTransfer,
    WiseBatch,
)
from app.services.audit_log import log_event
from app.core.config import settings


class WiseConnector:
    def __init__(self, db: Session, company_id: int, environment: str, actor_user_id: int | None = None):
        self.db = db
        self.company_id = company_id
        self.environment = environment
        self.actor_user_id = actor_user_id
        self.client = WiseApiClient(db, company_id, environment)
        self.endpoints = WiseEndpoints()

    def _credentials(self) -> IntegrationCredentialWise:
        creds = self.db.query(IntegrationCredentialWise).filter(
            IntegrationCredentialWise.company_id == self.company_id,
            IntegrationCredentialWise.wise_environment == self.environment,
        ).first()
        if not creds:
            raise RuntimeError("Wise credentials not found")
        return creds

    def sync_profiles(self) -> int:
        payload = self.client.request("GET", self.endpoints.profiles)
        profiles = payload if isinstance(payload, list) else payload.get("profiles") or []
        count = 0
        selected_profile_id = None
        for item in profiles:
            profile_id = str(item.get("id"))
            profile_type = item.get("type") or "unknown"
            existing = self.db.query(WiseProfile).filter(
                WiseProfile.company_id == self.company_id,
                WiseProfile.wise_profile_id == profile_id,
            ).first()
            if existing:
                existing.profile_type = profile_type
                existing.details = item
                existing.fetched_at = datetime.now(timezone.utc)
            else:
                self.db.add(WiseProfile(
                    company_id=self.company_id,
                    wise_profile_id=profile_id,
                    profile_type=profile_type,
                    details=item,
                    fetched_at=datetime.now(timezone.utc),
                ))
            count += 1
            if profile_type == "business" and not selected_profile_id:
                selected_profile_id = profile_id
        if not selected_profile_id and profiles:
            selected_profile_id = str(profiles[0].get("id"))
        if selected_profile_id:
            creds = self._credentials()
            creds.wise_profile_id = selected_profile_id
            creds.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        return count

    def sync_balance_accounts(self) -> int:
        creds = self._credentials()
        if not creds.wise_profile_id:
            raise RuntimeError("Wise profile not set")
        path = self.endpoints.balance_accounts.format(profile_id=creds.wise_profile_id)
        payload = self.client.request("GET", path)
        accounts = payload.get("balanceAccounts") if isinstance(payload, dict) else payload
        accounts = accounts or []
        count = 0
        for item in accounts:
            balance_id = str(item.get("id"))
            currency = item.get("currency") or item.get("balances", [{}])[0].get("currency")
            existing = self.db.query(WiseBalanceAccount).filter(
                WiseBalanceAccount.company_id == self.company_id,
                WiseBalanceAccount.wise_balance_account_id == balance_id,
            ).first()
            if existing:
                existing.currency = currency or existing.currency
                existing.name = item.get("name")
                existing.status = item.get("status")
                existing.details = item
                existing.fetched_at = datetime.now(timezone.utc)
            else:
                self.db.add(WiseBalanceAccount(
                    company_id=self.company_id,
                    wise_balance_account_id=balance_id,
                    wise_profile_id=creds.wise_profile_id,
                    currency=currency or "UNKNOWN",
                    name=item.get("name"),
                    status=item.get("status"),
                    details=item,
                    fetched_at=datetime.now(timezone.utc),
                ))
            account = self.db.query(BankAccount).filter(
                BankAccount.company_id == self.company_id,
                BankAccount.provider == "wise",
                BankAccount.provider_account_id == balance_id,
            ).first()
            if account:
                account.name = item.get("name") or account.name
                account.currency = currency or account.currency
            else:
                self.db.add(BankAccount(
                    company_id=self.company_id,
                    name=item.get("name") or f"Wise {balance_id}",
                    currency=currency or "USD",
                    balance=0.0,
                    provider="wise",
                    provider_account_id=balance_id,
                ))
            count += 1
        self.db.commit()
        return count

    def sync_balances(self) -> int:
        balances = self.db.query(WiseBalanceAccount).filter(
            WiseBalanceAccount.company_id == self.company_id
        ).all()
        count = 0
        for account in balances:
            path = self.endpoints.balances.format(balance_account_id=account.wise_balance_account_id)
            payload = self.client.request("GET", path)
            items = payload.get("balances") if isinstance(payload, dict) else payload
            items = items or []
            for item in items:
                currency = item.get("currency") or account.currency
                amount = float(item.get("amount") or item.get("value") or 0)
                timestamp = item.get("timestamp") or item.get("date") or datetime.now(timezone.utc).isoformat()
                captured_at = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
                self.db.add(WiseBalance(
                    company_id=self.company_id,
                    wise_balance_account_id=account.wise_balance_account_id,
                    currency=currency,
                    amount=amount,
                    timestamp=captured_at,
                    fetched_at=datetime.now(timezone.utc),
                ))
                bank_account = self.db.query(BankAccount).filter(
                    BankAccount.company_id == self.company_id,
                    BankAccount.provider == "wise",
                    BankAccount.provider_account_id == account.wise_balance_account_id,
                ).first()
                if bank_account:
                    bank_account.balance = amount
                    self.db.add(BankBalance(
                        company_id=self.company_id,
                        bank_account_id=bank_account.id,
                        provider="wise",
                        provider_account_id=account.wise_balance_account_id,
                        currency=currency,
                        balance=amount,
                        captured_at=captured_at,
                    ))
                count += 1
        self.db.commit()
        return count

    def sync_transactions(self) -> int:
        creds = self._credentials()
        cursor_map = creds.sync_cursor_transactions or {}
        total = 0
        accounts = self.db.query(WiseBalanceAccount).filter(
            WiseBalanceAccount.company_id == self.company_id
        ).all()
        for account in accounts:
            cursor = cursor_map.get(account.wise_balance_account_id)
            params = {
                "balanceAccountId": account.wise_balance_account_id,
            }
            if cursor:
                params["cursor"] = cursor
            payload = self.client.request("GET", self.endpoints.transactions, params=params)
            transactions = payload.get("transactions") if isinstance(payload, dict) else payload
            transactions = transactions or []
            for item in transactions:
                transaction_id = str(item.get("id") or item.get("transactionId"))
                occurred_at = item.get("date") or item.get("occurred_at") or datetime.now(timezone.utc).isoformat()
                occurred_dt = datetime.fromisoformat(str(occurred_at).replace("Z", "+00:00"))
                amount = float(item.get("amount") or item.get("value") or 0)
                currency = item.get("currency") or account.currency or "USD"
                existing = self.db.query(WiseTransactionRaw).filter(
                    WiseTransactionRaw.company_id == self.company_id,
                    WiseTransactionRaw.wise_transaction_id == transaction_id,
                ).first()
                if existing:
                    existing.occurred_at = occurred_dt
                    existing.amount = amount
                    existing.currency = currency
                    existing.description = item.get("description")
                    existing.raw = item
                    existing.fetched_at = datetime.now(timezone.utc)
                else:
                    self.db.add(WiseTransactionRaw(
                        company_id=self.company_id,
                        wise_transaction_id=transaction_id,
                        wise_balance_account_id=account.wise_balance_account_id,
                        occurred_at=occurred_dt,
                        amount=amount,
                        currency=currency,
                        description=item.get("description"),
                        raw=item,
                        fetched_at=datetime.now(timezone.utc),
                    ))
                bank_account = self.db.query(BankAccount).filter(
                    BankAccount.company_id == self.company_id,
                    BankAccount.provider == "wise",
                    BankAccount.provider_account_id == account.wise_balance_account_id,
                ).first()
                if bank_account:
                    existing_tx = self.db.query(BankTransaction).filter(
                        BankTransaction.company_id == self.company_id,
                        BankTransaction.provider == "wise",
                        BankTransaction.provider_transaction_id == transaction_id,
                    ).first()
                    if existing_tx:
                        existing_tx.amount = amount
                        existing_tx.currency = currency
                        existing_tx.posted_at = occurred_dt.date()
                        existing_tx.description = item.get("description")
                        existing_tx.raw_reference = item.get("reference")
                    else:
                        self.db.add(BankTransaction(
                            bank_account_id=bank_account.id,
                            company_id=self.company_id,
                            posted_at=occurred_dt.date(),
                            amount=amount,
                            currency=currency,
                            description=item.get("description"),
                            category=item.get("type"),
                            provider="wise",
                            provider_transaction_id=transaction_id,
                            raw_reference=item.get("reference"),
                        ))
                total += 1
            cursor_map[account.wise_balance_account_id] = payload.get("nextCursor") if isinstance(payload, dict) else cursor
        creds.sync_cursor_transactions = cursor_map
        creds.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        return total

    def register_webhooks(self) -> str | None:
        existing = self.db.query(WiseWebhookSubscription).filter(
            WiseWebhookSubscription.company_id == self.company_id,
            WiseWebhookSubscription.status == "active",
            WiseWebhookSubscription.wise_environment == self.environment,
        ).first()
        if existing:
            return existing.wise_subscription_id
        callback_url = settings.wise_webhook_url or settings.wise_redirect_uri.replace("/connectors/wise/oauth/callback", "/webhooks/wise")
        payload = {
            "name": f"aicfo-{self.company_id}",
            "callbackURL": callback_url,
            "eventTypes": ["balance-updated", "transaction-created", "transfer-state-change"],
        }
        response = self.client.request("POST", self.endpoints.webhooks, json=payload)
        subscription_id = str(response.get("id"))
        secret_ref = response.get("secret") or settings.wise_webhook_secret
        self.db.add(WiseWebhookSubscription(
            company_id=self.company_id,
            wise_subscription_id=subscription_id,
            wise_environment=self.environment,
            event_types=payload["eventTypes"],
            status="active",
            secret_ref=secret_ref,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ))
        self.db.commit()
        return subscription_id

    def create_transfer(self, payee_id: str, amount: float, currency: str, reference: str, idempotency_key: str) -> WiseTransfer:
        if not settings.wise_write_enabled:
            raise RuntimeError("Wise write mode disabled")
        transfer = WiseTransfer(
            company_id=self.company_id,
            status="created",
            reference=reference,
            idempotency_key=idempotency_key,
            created_by_user_id=self.actor_user_id,
            approvals=[],
        )
        self.db.add(transfer)
        self.db.flush()
        payload = {
            "payeeId": payee_id,
            "amount": amount,
            "currency": currency,
            "reference": reference,
        }
        response = self.client.request("POST", self.endpoints.transfers, json=payload)
        transfer.wise_transfer_id = str(response.get("id"))
        transfer.raw = response
        transfer.updated_at = datetime.now(timezone.utc)
        log_event(self.db, self.company_id, "wise.transfer.created", "wise_transfer", str(transfer.id), self.actor_user_id, payload)
        self.db.commit()
        return transfer

    def create_batch_group(self, reference: str, idempotency_key: str) -> WiseBatch:
        if not settings.wise_write_enabled:
            raise RuntimeError("Wise write mode disabled")
        batch = WiseBatch(
            company_id=self.company_id,
            status="created",
            reference=reference,
            idempotency_key=idempotency_key,
            created_by_user_id=self.actor_user_id,
            approvals=[],
        )
        self.db.add(batch)
        self.db.flush()
        payload = {"reference": reference}
        response = self.client.request("POST", self.endpoints.batch_groups, json=payload)
        batch.wise_batch_id = str(response.get("id"))
        batch.raw = response
        batch.updated_at = datetime.now(timezone.utc)
        log_event(self.db, self.company_id, "wise.batch.created", "wise_batch", str(batch.id), self.actor_user_id, payload)
        self.db.commit()
        return batch

    def add_transfer_to_batch(self, batch_id: str, transfer_payload: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        if not settings.wise_write_enabled:
            raise RuntimeError("Wise write mode disabled")
        payload = transfer_payload | {"idempotencyKey": idempotency_key}
        response = self.client.request(
            "POST",
            self.endpoints.batch_payments.format(batch_id=batch_id),
            json=payload,
        )
        log_event(self.db, self.company_id, "wise.batch.add_transfer", "wise_batch", batch_id, self.actor_user_id, payload)
        return response

    def fund_batch(self, batch_id: str, idempotency_key: str) -> dict[str, Any]:
        if not settings.wise_write_enabled:
            raise RuntimeError("Wise write mode disabled")
        payload = {"idempotencyKey": idempotency_key}
        response = self.client.request(
            "POST",
            self.endpoints.batch_funding.format(batch_id=batch_id),
            json=payload,
        )
        log_event(self.db, self.company_id, "wise.batch.funded", "wise_batch", batch_id, self.actor_user_id, payload)
        return response
