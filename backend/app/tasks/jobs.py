from app.tasks.celery_app import celery_app


@celery_app.task
def sync_shopify():
    return {"status": "success", "message": "Shopify sync completed."}


@celery_app.task
def recompute_metrics():
    return {"status": "success", "message": "Metrics recomputed."}
