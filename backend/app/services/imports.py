import csv
from datetime import datetime
from io import StringIO
from sqlalchemy.orm import Session
from app.models.models import BankAccount, BankTransaction, Bill, Supplier, PurchaseOrder, PurchaseOrderLine


def import_bank_csv(db: Session, company_id: int, content: str) -> int:
    reader = csv.DictReader(StringIO(content))
    account = db.query(BankAccount).filter(BankAccount.company_id == company_id).first()
    if not account:
        account = BankAccount(company_id=company_id, name="Primary", currency="USD", balance=0.0, provider="manual")
        db.add(account)
        db.flush()
    count = 0
    for row in reader:
        txn = BankTransaction(
            bank_account_id=account.id,
            company_id=company_id,
            posted_at=datetime.strptime(row["posted_at"], "%Y-%m-%d").date(),
            amount=float(row["amount"]),
            currency=row.get("currency"),
            description=row.get("description", ""),
            category=row.get("category", ""),
            provider="manual",
        )
        db.add(txn)
        count += 1
    db.commit()
    return count


def import_payables_csv(db: Session, company_id: int, content: str) -> int:
    reader = csv.DictReader(StringIO(content))
    count = 0
    for row in reader:
        bill = Bill(
            company_id=company_id,
            vendor=row["vendor"],
            amount=float(row["amount"]),
            due_date=datetime.strptime(row["due_date"], "%Y-%m-%d").date(),
            status=row.get("status", "open"),
            criticality=row.get("criticality", "deferrable"),
        )
        db.add(bill)
        count += 1
    db.commit()
    return count


def import_po_csv(db: Session, company_id: int, content: str) -> int:
    reader = csv.DictReader(StringIO(content))
    supplier_cache = {}
    count = 0
    for row in reader:
        supplier_name = row["supplier"]
        supplier = supplier_cache.get(supplier_name)
        if not supplier:
            supplier = Supplier(company_id=company_id, name=supplier_name)
            db.add(supplier)
            db.flush()
            supplier_cache[supplier_name] = supplier
        po = PurchaseOrder(
            company_id=company_id,
            supplier_id=supplier.id,
            status=row.get("status", "open"),
            created_at=datetime.strptime(row["created_at"], "%Y-%m-%d"),
            promised_date=datetime.strptime(row["promised_date"], "%Y-%m-%d").date() if row.get("promised_date") else None,
            received_date=datetime.strptime(row["received_date"], "%Y-%m-%d").date() if row.get("received_date") else None,
        )
        db.add(po)
        db.flush()
        line = PurchaseOrderLine(
            purchase_order_id=po.id,
            company_id=company_id,
            sku=row["sku"],
            quantity=int(row["quantity"]),
            unit_cost=float(row["unit_cost"]),
        )
        db.add(line)
        count += 1
    db.commit()
    return count
