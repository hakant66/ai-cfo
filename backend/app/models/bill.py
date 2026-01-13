from sqlalchemy import Column, Date, DateTime, Integer, Numeric, String
from sqlalchemy.sql import func

from app.db.base import Base


class Bill(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False)
    vendor = Column(String, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    due_date = Column(Date, nullable=False)
    priority = Column(String, default="deferrable")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
