from app.integrations.base import Connector


class BankingConnector(Connector):
    def test(self) -> dict:
        return {"ok": False, "message": "Banking connector not configured. Use CSV import."}

    def sync(self) -> dict:
        return {"ok": False, "message": "Banking sync is a stub in MVP."}