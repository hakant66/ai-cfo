from sqlalchemy import Column, Date, DateTime, Integer, Numeric, String
from sqlalchemy.sql import func

from app.db.base import Base


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    balance = Column(Numeric(12, 2), default=0)
    currency = Column(String, default="USD")
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False)
    account_id = Column(Integer, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    posted_date = Column(Date, nullable=False)
    description = Column(String, nullable=True)
