from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import create_token, hash_password, verify_password
from app import models, schemas
from app.deps import get_current_user, require_roles

router = APIRouter(prefix="/auth", tags=["auth"])
admin = Depends(require_roles("admin"))

@router.post("/register", response_model=dict)
def register(
    d: schemas.UserCreate,
    db: Session = Depends(get_db),
    actual: models.User | None = Depends(get_current_user),
):
    # Bootstrap: si no hay ningún usuario, se permite crear el primero sin token.
    # Después solo un admin puede crear usuarios.
    if db.query(models.User).count() > 0:
        if actual is None or not actual.activo:
            raise HTTPException(401, "No autenticado")
        if actual.rol != "admin":
            raise HTTPException(403, "Solo un admin puede crear usuarios")
    if db.query(models.User).filter(models.User.username == d.username).first():
        raise HTTPException(400, "Usuario ya existe")
    u = models.User(username=d.username, hashed_password=hash_password(d.password), rol=d.rol)
    db.add(u); db.commit()
    return {"ok": True, "username": u.username, "rol": u.rol}

@router.post("/login", response_model=dict)
def login(d: schemas.LoginIn, db: Session = Depends(get_db)):
    u = db.query(models.User).filter(models.User.username == d.username).first()
    if not u or not u.activo or not verify_password(d.password, u.hashed_password):
        raise HTTPException(401, "Credenciales invalidas")
    return {"access_token": create_token(u.username, u.rol), "token_type": "bearer",
            "rol": u.rol, "username": u.username}

@router.get("/users", response_model=list[dict], dependencies=[admin])
def list_users(db: Session = Depends(get_db)):
    return [{"id": u.id, "username": u.username, "rol": u.rol, "activo": u.activo}
            for u in db.query(models.User).order_by(models.User.username).all()]

@router.get("/me", response_model=dict)
def me(actual: models.User | None = Depends(get_current_user)):
    if actual is None or not actual.activo:
        raise HTTPException(401, "No autenticado")
    return {"username": actual.username, "rol": actual.rol}

@router.post("/password", response_model=dict)
def change_password(d: dict, db: Session = Depends(get_db), actual: models.User | None = Depends(get_current_user)):
    if actual is None or not actual.activo:
        raise HTTPException(401, "No autenticado")
    if not d.get("current") or not verify_password(d["current"], actual.hashed_password):
        raise HTTPException(401, "Contraseña actual incorrecta")
    nueva = d.get("new") or ""
    if len(nueva) < 6 or len(nueva) > 100:
        raise HTTPException(422, "La nueva contraseña debe tener entre 6 y 100 caracteres")
    actual.hashed_password = hash_password(nueva)
    db.commit()
    return {"ok": True}
