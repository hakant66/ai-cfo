from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.db.base import Base


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False)
    provider = Column(String, nullable=False)
    status = Column(String, default="disconnected")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
