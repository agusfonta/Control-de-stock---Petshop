from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app import models, schemas
from app.deps import require_roles

router = APIRouter(prefix="/clientes", tags=["clientes"])
leer = Depends(require_roles("admin", "vendedor"))

@router.post("", response_model=schemas.ClienteOut, status_code=201, dependencies=[leer])
def crear(d: schemas.ClienteCreate, db: Session = Depends(get_db)):
    if db.query(models.Cliente).filter((models.Cliente.email == d.email) | (models.Cliente.dni == d.dni)).first():
        raise HTTPException(400, "Email o DNI ya registrado")
    c = models.Cliente(**d.model_dump())
    db.add(c); db.commit(); db.refresh(c)
    return c

@router.get("", response_model=list[schemas.ClienteOut], dependencies=[leer])
def listar(db: Session = Depends(get_db)):
    return db.query(models.Cliente).order_by(models.Cliente.nombre).all()

@router.get("/{cid}", response_model=schemas.ClienteOut, dependencies=[leer])
def obtener(cid: int, db: Session = Depends(get_db)):
    c = db.get(models.Cliente, cid)
    if not c: raise HTTPException(404, "Cliente no encontrado")
    return c

@router.get("/{cid}/pedidos", response_model=list[schemas.PedidoOut], dependencies=[leer])
def pedidos_de_cliente(cid: int, db: Session = Depends(get_db)):
    c = db.get(models.Cliente, cid)
    if not c: raise HTTPException(404, "Cliente no encontrado")
    return db.query(models.Pedido).options(joinedload(models.Pedido.detalles)).filter(models.Pedido.cliente_id == cid).order_by(models.Pedido.fecha.desc()).all()
