from sqlalchemy.orm import Session
from app.models.models import Integration, IntegrationType, Bill, BankTransaction, BankAccount


def compute_confidence(db: Session, company_id: int) -> str:
    has_shopify = db.query(Integration).filter(
        Integration.company_id == company_id,
        Integration.type == IntegrationType.shopify,
        Integration.status == "connected",
    ).first() is not None

    has_bank = db.query(BankTransaction).join(BankAccount, BankTransaction.bank_account_id == BankAccount.id).filter(
        BankAccount.company_id == company_id
    ).count() > 0

    has_payables = db.query(Bill).filter(Bill.company_id == company_id).count() > 0

    if has_shopify and has_bank and has_payables:
        return "High"
    if has_shopify and (has_bank or has_payables):
        return "Medium"
    if has_shopify:
        return "Low"
    return "Low"