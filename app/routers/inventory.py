from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app import models, schemas
from app.deps import require_roles

router = APIRouter(tags=["stock"])
leer = Depends(require_roles("admin", "vendedor"))
admin = Depends(require_roles("admin"))

def _parse_fecha(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        raise HTTPException(422, f"Fecha inválida '{s}': usar formato YYYY-MM-DD")

@router.post("/productos/{pid}/stock/ingreso", response_model=schemas.MovimientoOut, dependencies=[leer])
def ingreso(pid: int, d: schemas.IngresoStockIn, db: Session = Depends(get_db)):
    p = db.get(models.Producto, pid)
    if not p: raise HTTPException(404, "Producto no encontrado")
    ant = p.stock
    p.stock = ant + d.cantidad
    m = models.MovimientoStock(producto_id=p.id, tipo=models.TipoMovimiento.INGRESO,
                               cantidad=d.cantidad, stock_anterior=ant, stock_nuevo=p.stock)
    db.add(m); db.commit(); db.refresh(m)
    return m

@router.get("/stock/movimientos", response_model=list[schemas.MovimientoOut], dependencies=[leer])
def movimientos(
    producto_id: int | None = None,
    fecha: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.MovimientoStock).order_by(models.MovimientoStock.fecha.desc())
    if producto_id:
        q = q.filter(models.MovimientoStock.producto_id == producto_id)
    if fecha:
        ini = _parse_fecha(fecha)
        q = q.filter(models.MovimientoStock.fecha >= ini, models.MovimientoStock.fecha < ini + timedelta(days=1))
    if desde:
        q = q.filter(models.MovimientoStock.fecha >= _parse_fecha(desde))
    if hasta:
        q = q.filter(models.MovimientoStock.fecha < _parse_fecha(hasta) + timedelta(days=1))
    return q.limit(500).all()

prov = APIRouter(prefix="/proveedores", tags=["proveedores"])

@prov.post("", response_model=schemas.ProveedorOut, status_code=201, dependencies=[leer])
def crear_prov(d: schemas.ProveedorCreate, db: Session = Depends(get_db)):
    if db.query(models.Proveedor).filter(models.Proveedor.nombre == d.nombre).first():
        raise HTTPException(400, "Proveedor ya existe")
    pr = models.Proveedor(**d.model_dump())
    db.add(pr); db.commit(); db.refresh(pr)
    return pr

@prov.get("", response_model=list[schemas.ProveedorOut], dependencies=[leer])
def listar_prov(db: Session = Depends(get_db)):
    return db.query(models.Proveedor).all()

rep = APIRouter(prefix="/reportes", tags=["reportes"])

@rep.get("/ventas", dependencies=[leer])
def ventas(fecha: str | None = None, desde: str | None = None, hasta: str | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Pedido).filter(models.Pedido.estado == models.EstadoPedido.pagado)
    if fecha:
        ini = _parse_fecha(fecha)
        q = q.filter(models.Pedido.fecha >= ini, models.Pedido.fecha < ini + timedelta(days=1))
    if desde:
        q = q.filter(models.Pedido.fecha >= _parse_fecha(desde))
    if hasta:
        q = q.filter(models.Pedido.fecha < _parse_fecha(hasta) + timedelta(days=1))
    pedidos = q.all()
    return {"cantidad_pedidos": len(pedidos), "total_ars": round(sum(p.total for p in pedidos), 2)}
