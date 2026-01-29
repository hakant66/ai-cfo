from app.integrations.base import Connector


class MarketingConnector(Connector):
    def test(self) -> dict:
        return {"ok": False, "message": "Marketing connector not configured. Use stub data."}

    def sync(self) -> dict:
        return {"ok": False, "message": "Marketing sync is a stub in MVP."}