from pydantic import BaseModel, EmailStr

class User(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None
    is_superadmin: bool

    class Config:
        from_attributes = True
