from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.db.base import Base


class MetricRun(Base):
    __tablename__ = "metric_runs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False)
    metric_name = Column(String, nullable=False)
    provenance = Column(String, nullable=False)
    source_systems = Column(String, nullable=False)
    window = Column(String, nullable=False)
    currency = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
