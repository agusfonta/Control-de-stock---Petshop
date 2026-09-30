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
    payload = d.model_dump(exclude={"mascotas"})
    c = models.Cliente(**payload)
    c.mascotas = [models.Mascota(**m) for m in d.model_dump().get("mascotas", [])]
    db.add(c); db.commit(); db.refresh(c)
    return c

@router.get("", response_model=list[schemas.ClienteOut], dependencies=[leer])
def listar(db: Session = Depends(get_db)):
    return db.query(models.Cliente).options(joinedload(models.Cliente.mascotas)).order_by(models.Cliente.nombre).all()

@router.get("/{cid}", response_model=schemas.ClienteOut, dependencies=[leer])
def obtener(cid: int, db: Session = Depends(get_db)):
    c = db.query(models.Cliente).options(joinedload(models.Cliente.mascotas)).filter(models.Cliente.id == cid).first()
    if not c: raise HTTPException(404, "Cliente no encontrado")
    return c

@router.get("/{cid}/pedidos", response_model=list[schemas.PedidoOut], dependencies=[leer])
def pedidos_de_cliente(cid: int, db: Session = Depends(get_db)):
    c = db.get(models.Cliente, cid)
    if not c: raise HTTPException(404, "Cliente no encontrado")
    pedidos = db.query(models.Pedido).options(joinedload(models.Pedido.detalles), joinedload(models.Pedido.pagos), joinedload(models.Pedido.vendedora)).filter(models.Pedido.cliente_id == cid).order_by(models.Pedido.fecha.desc()).all()
    for p in pedidos:
        p.vendedora_nombre = p.vendedora.username if p.vendedora else None
        if not p.pagos:
            p.pagos = [models.PagoPedido(id=0, pedido_id=p.id, metodo=p.metodo_pago, monto=p.total)]
            p.es_mixto = False
        else:
            p.es_mixto = len(p.pagos) > 1
    return pedidos
