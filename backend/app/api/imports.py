from fastapi import APIRouter, UploadFile

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/bank_csv")
def import_bank_csv(file: UploadFile):
    return {"status": "received", "filename": file.filename}


@router.post("/payables_csv")
def import_payables_csv(file: UploadFile):
    return {"status": "received", "filename": file.filename}


@router.post("/po_csv")
def import_po_csv(file: UploadFile):
    return {"status": "received", "filename": file.filename}
