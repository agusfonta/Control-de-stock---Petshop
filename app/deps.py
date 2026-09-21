from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models import User

oauth = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(token: str | None = Depends(oauth), db: Session = Depends(get_db)) -> User | None:
    if not token:
        return None
    try:
        payload = decode_token(token)
        user = db.query(User).filter(User.username == payload.get("sub")).first()
        return user
    except Exception:
        return None


def require_roles(*roles: str):
    def _dep(user: User | None = Depends(get_current_user)):
        if user is None or not user.activo:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado")
        if roles and user.rol not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin permiso")
        return user
    return _dep
