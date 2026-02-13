from pydantic import BaseModel, EmailStr

class User(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None
    is_superadmin: bool

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    is_superadmin: bool | None = None
    password: str | None = None
