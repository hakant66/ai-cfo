from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any


class CompanyCreate(BaseModel):
    name: str
    website: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    currency: str = "USD"
    timezone: str = "UTC"
    settlement_lag_days: int = 2
    thresholds: Optional[Dict[str, Any]] = None




class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    currency: Optional[str] = None
    timezone: Optional[str] = None
    settlement_lag_days: Optional[int] = None
    thresholds: Optional[Dict[str, Any]] = None


class CompanyOut(BaseModel):
    id: int
    name: str
    website: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    currency: str
    timezone: str
    settlement_lag_days: int
    thresholds: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class CompanyPublic(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)
