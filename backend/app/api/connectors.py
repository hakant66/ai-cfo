from fastapi import APIRouter

router = APIRouter(prefix="/connectors", tags=["connectors"])


@router.post("/shopify/test")
def test_shopify_connector():
    return {"status": "ok", "message": "Shopify connector reachable (demo)."}


@router.post("/shopify/sync")
def sync_shopify_connector():
    return {"status": "queued", "job": "shopify_sync"}
