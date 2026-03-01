from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.security import ALGORITHM, SECRET_KEY


def get_rate_limit_key(request: Request) -> str:
    """
    Rate limit by authenticated user when possible, otherwise by IP.
    Avoids blocking all users behind the same NAT (e.g. school WiFi) when one
    user hits the limit.
    """
    token = request.cookies.get("access_token") if request.cookies else None
    if not token or not token.strip():
        return f"ip:{get_remote_address(request)}"
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return f"ip:{get_remote_address(request)}"
        sub = payload.get("sub")
        if not sub:
            return f"ip:{get_remote_address(request)}"
        return f"user:{sub}"
    except JWTError:
        return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=get_rate_limit_key)
