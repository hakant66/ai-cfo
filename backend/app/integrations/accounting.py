from app.integrations.base import Connector


class AccountingConnector(Connector):
    def test(self) -> dict:
        return {"ok": False, "message": "Accounting connector not configured. Use CSV import."}

    def sync(self) -> dict:
        return {"ok": False, "message": "Accounting sync is a stub in MVP."}