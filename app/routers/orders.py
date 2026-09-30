from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app import models, schemas
from app.deps import require_roles
from app.services import sales as sales_service
from app.core.time import local_day_bounds_utc

router = APIRouter(prefix="/pedidos", tags=["pedidos"])
leer = Depends(require_roles("admin", "vendedor"))

def _parse_fecha(s: str) -> date:
    try:
        return datetime.fromisoformat(s).date()
    except (ValueError, TypeError):
        raise HTTPException(422, f"Fecha inválida '{s}': usar formato YYYY-MM-DD")

def _preparar_respuesta(ped: models.Pedido) -> models.Pedido:
    """Completa pagos/es_mixto/vendedora para serializar; ventas pre-migración usan fallback legacy."""
    ped.vendedora_nombre = ped.vendedora.username if ped.vendedora else None
    reales = list(ped.pagos) if ped.pagos else []
    if not reales:
        ped.pagos = [models.PagoPedido(id=0, pedido_id=ped.id, metodo=ped.metodo_pago, monto=ped.total)]
        ped.es_mixto = False
    else:
        ped.es_mixto = len(reales) > 1
    return ped

@router.post("", response_model=schemas.PedidoOut, status_code=201, dependencies=[leer])
def crear(d: schemas.PedidoCreate, db: Session = Depends(get_db), vendedor: models.User = Depends(require_roles("admin", "vendedor"))):
    try:
        ped = sales_service.crear_venta(db, d, vendedor)
    except sales_service.SalesError as e:
        db.rollback()
        raise HTTPException(e.status_code, e.detail)
    return _preparar_respuesta(ped)

@router.get("", response_model=list[schemas.PedidoOut], dependencies=[leer])
def listar(fecha: str | None = None, desde: str | None = None, hasta: str | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Pedido).options(joinedload(models.Pedido.detalles), joinedload(models.Pedido.pagos), joinedload(models.Pedido.vendedora))
    if fecha:
        ini, fin = local_day_bounds_utc(_parse_fecha(fecha))
        q = q.filter(models.Pedido.fecha >= ini, models.Pedido.fecha < fin)
    if desde:
        q = q.filter(models.Pedido.fecha >= local_day_bounds_utc(_parse_fecha(desde))[0])
    if hasta:
        q = q.filter(models.Pedido.fecha < local_day_bounds_utc(_parse_fecha(hasta))[1])
    peds = q.order_by(models.Pedido.fecha.desc()).all()
    return [_preparar_respuesta(p) for p in peds]

@router.get("/{pid}", response_model=schemas.PedidoOut, dependencies=[leer])
def obtener(pid: int, db: Session = Depends(get_db)):
    p = db.query(models.Pedido).options(joinedload(models.Pedido.detalles), joinedload(models.Pedido.pagos), joinedload(models.Pedido.vendedora)).filter(models.Pedido.id == pid).first()
    if not p: raise HTTPException(404, "Pedido no encontrado")
    return _preparar_respuesta(p)

@router.patch("/{pid}/cancelar", response_model=schemas.PedidoOut, dependencies=[leer])
def cancelar(pid: int, db: Session = Depends(get_db)):
    try:
        ped = sales_service.cancelar_venta(db, pid)
    except sales_service.SalesError as e:
        db.rollback()
        raise HTTPException(e.status_code, e.detail)
    return _preparar_respuesta(ped)
