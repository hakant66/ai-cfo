from pydantic import BaseModel, ConfigDict, field_validator
from email_validator import validate_email
from app.models.models import Role


class UserCreate(BaseModel):
    email: str
    password: str
    company_name: str
    role: Role

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, value: str) -> str:
        return validate_email(value, check_deliverability=False).email


class UserLogin(BaseModel):
    email: str
    password: str
    company_id: int | None = None

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, value: str) -> str:
        return validate_email(value, check_deliverability=False).email


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    role: Role
    company_id: int

    model_config = ConfigDict(from_attributes=True)


class AdminUserCreate(BaseModel):
    email: str
    password: str
    role: Role
    company_id: int

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, value: str) -> str:
        return validate_email(value, check_deliverability=False).email


class AdminUserUpdate(BaseModel):
    email: str | None = None
    password: str | None = None
    role: Role | None = None

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_email(value, check_deliverability=False).email
