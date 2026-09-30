from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app import models, schemas
from app.deps import require_roles
from app.services import stock as stock_service
from app.services import cash as cash_service
from app.services.money import money
from app.core.time import local_day_bounds_utc, local_datetime_to_utc_naive, utc_now

router = APIRouter(tags=["stock"])
leer = Depends(require_roles("admin", "vendedor"))
admin = Depends(require_roles("admin"))

def _parse_fecha(s: str):
    try:
        from datetime import datetime as _datetime
        return _datetime.fromisoformat(s).date()
    except (ValueError, TypeError):
        raise HTTPException(422, f"Fecha inválida '{s}': usar formato YYYY-MM-DD")

@router.post("/productos/{pid}/stock/ingreso", response_model=schemas.MovimientoOut, dependencies=[leer])
def ingreso(pid: int, d: schemas.IngresoStockIn, db: Session = Depends(get_db)):
    p = db.get(models.Producto, pid)
    if not p: raise HTTPException(404, "Producto no encontrado")
    try:
        m = stock_service.ingresar(db, p, d.cantidad)
    except stock_service.StockError as e:
        db.rollback()
        raise HTTPException(422, str(e))
    db.commit(); db.refresh(m)
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
        ini, fin = local_day_bounds_utc(_parse_fecha(fecha))
        q = q.filter(models.MovimientoStock.fecha >= ini, models.MovimientoStock.fecha < fin)
    if desde:
        q = q.filter(models.MovimientoStock.fecha >= local_day_bounds_utc(_parse_fecha(desde))[0])
    if hasta:
        q = q.filter(models.MovimientoStock.fecha < local_day_bounds_utc(_parse_fecha(hasta))[1])
    return q.limit(500).all()

prov = APIRouter(prefix="/proveedores", tags=["proveedores"])

def _proveedor_out(pr: models.Proveedor) -> schemas.ProveedorOut:
    o = schemas.ProveedorOut.model_validate(pr)
    o.pronto_pago_porcentaje = float(pr.pronto_pago_porcentaje) if pr.pronto_pago_porcentaje is not None else None
    return o


@prov.post("", response_model=schemas.ProveedorOut, status_code=201, dependencies=[leer])
def crear_prov(d: schemas.ProveedorCreate, db: Session = Depends(get_db)):
    if db.query(models.Proveedor).filter(models.Proveedor.nombre == d.nombre).first():
        raise HTTPException(400, "Proveedor ya existe")
    pr = models.Proveedor(**d.model_dump())
    db.add(pr); db.commit(); db.refresh(pr)
    return _proveedor_out(pr)

@prov.get("", response_model=list[schemas.ProveedorOut], dependencies=[leer])
def listar_prov(db: Session = Depends(get_db)):
    return [_proveedor_out(pr) for pr in db.query(models.Proveedor).all()]


SIGNO_DEUDA = {
    models.TipoMovProveedor.BOLETA_001: 1,
    models.TipoMovProveedor.PAGO_EFECTIVO_002: -1,
    models.TipoMovProveedor.PAGO_TRANSFER_003: -1,
    models.TipoMovProveedor.NOTA_CREDITO_004: -1,
}


def _con_saldo(movs: list[models.MovimientoProveedor]) -> list[schemas.MovimientoProveedorOut]:
    """Suma corrida por proveedor (orden cronológico): boleta 001 suma, resto resta."""
    out, acc = [], money(0)
    for m in sorted(movs, key=lambda x: (x.fecha, x.id)):
        acc = money(acc + SIGNO_DEUDA[m.tipo] * m.monto)
        o = schemas.MovimientoProveedorOut.model_validate(m)
        o.pago = float(m.monto) if m.tipo != models.TipoMovProveedor.BOLETA_001 else 0.0
        o.saldo_boleta = float(m.monto) if m.tipo == models.TipoMovProveedor.BOLETA_001 else 0.0
        o.saldo = float(acc)
        out.append(o)
    return out



@prov.patch("/{pid}", response_model=schemas.ProveedorOut, dependencies=[leer])
def actualizar_prov(pid: int, d: schemas.ProveedorUpdate, db: Session = Depends(get_db)):
    pr = db.get(models.Proveedor, pid)
    if not pr:
        raise HTTPException(404, "Proveedor no encontrado")
    data = d.model_dump(exclude_unset=True)
    if "nombre" in data:
        existe = db.query(models.Proveedor).filter(models.Proveedor.nombre == data["nombre"], models.Proveedor.id != pid).first()
        if existe:
            raise HTTPException(400, "Proveedor ya existe")
    for k, v in data.items():
        setattr(pr, k, v)
    db.commit(); db.refresh(pr)
    return _proveedor_out(pr)

@prov.get("/saldos", dependencies=[leer])
def saldos_prov(db: Session = Depends(get_db)):
    """Deuda actual por proveedor (para las pestañas tipo AMICO/Canalú)."""
    res = []
    for pr in db.query(models.Proveedor).all():
        movs = db.query(models.MovimientoProveedor).filter(
            models.MovimientoProveedor.proveedor_id == pr.id).all()
        saldo = money(sum((SIGNO_DEUDA[m.tipo] * m.monto for m in movs), money(0)))
        res.append({"id": pr.id, "nombre": pr.nombre, "alias": pr.alias,
                    "dias_entrega": pr.dias_entrega, "saldo": saldo,
                    "movimientos": len(movs)})
    return res


@prov.get("/{pid}/movimientos", response_model=list[schemas.MovimientoProveedorOut], dependencies=[leer])
def movs_prov(pid: int, db: Session = Depends(get_db)):
    if not db.get(models.Proveedor, pid):
        raise HTTPException(404, "Proveedor no encontrado")
    movs = db.query(models.MovimientoProveedor).filter(
        models.MovimientoProveedor.proveedor_id == pid).all()
    return _con_saldo(movs)


@prov.post("/{pid}/movimientos", response_model=schemas.MovimientoProveedorOut, status_code=201, dependencies=[leer])
def crear_mov_prov(pid: int, d: schemas.MovimientoProveedorCreate, db: Session = Depends(get_db)):
    pr = db.get(models.Proveedor, pid)
    if not pr:
        raise HTTPException(404, "Proveedor no encontrado")
    m = models.MovimientoProveedor(
        proveedor_id=pid, tipo=d.tipo, nro=d.nro.strip(),
        monto=d.monto, fecha=local_datetime_to_utc_naive(d.fecha) if d.fecha else utc_now())
    db.add(m); db.flush()
    if d.tipo in (models.TipoMovProveedor.PAGO_EFECTIVO_002,
                  models.TipoMovProveedor.PAGO_TRANSFER_003):
        medio = (models.MetodoPago.efectivo
                 if d.tipo == models.TipoMovProveedor.PAGO_EFECTIVO_002
                 else models.MetodoPago.qr)
        cash_service.registrar(
            db,
            tipo=models.TipoMovCaja.SALIDA,
            medio=medio,
            descripcion=f"Pago {pr.nombre} {m.nro}",
            monto=d.monto,
            fecha=m.fecha,
        )
    db.commit(); db.refresh(m)
    previos = db.query(models.MovimientoProveedor).filter(
        models.MovimientoProveedor.proveedor_id == pid).all()
    return _con_saldo(previos)[-1]

rep = APIRouter(prefix="/reportes", tags=["reportes"])

@rep.get("/ventas", dependencies=[leer])
def ventas(fecha: str | None = None, desde: str | None = None, hasta: str | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Pedido).filter(models.Pedido.estado == models.EstadoPedido.pagado)
    if fecha:
        ini, fin = local_day_bounds_utc(_parse_fecha(fecha))
        q = q.filter(models.Pedido.fecha >= ini, models.Pedido.fecha < fin)
    if desde:
        q = q.filter(models.Pedido.fecha >= local_day_bounds_utc(_parse_fecha(desde))[0])
    if hasta:
        q = q.filter(models.Pedido.fecha < local_day_bounds_utc(_parse_fecha(hasta))[1])
    pedidos = q.all()
    return {"cantidad_pedidos": len(pedidos), "total_ars": money(sum((p.total for p in pedidos), money(0)))}
