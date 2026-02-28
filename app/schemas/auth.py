from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if not any(c.isupper() for c in v):
            raise ValueError("La contraseña debe tener al menos una letra mayúscula")
        if not any(c.isdigit() for c in v):
            raise ValueError("La contraseña debe tener al menos un número")
        return v


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str