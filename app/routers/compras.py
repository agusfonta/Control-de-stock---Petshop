from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app import models, schemas
from app.deps import require_roles
from app.services import purchases as purchase_service
from app.core.time import local_day_bounds_utc
from app.services.money import money
from app.core.time import utc_now
from datetime import timedelta

router = APIRouter(prefix="/compras", tags=["compras"])
leer = Depends(require_roles("admin", "vendedor"))


def _parse_fecha(s: str):
    try:
        from datetime import datetime
        return datetime.fromisoformat(s).date()
    except (ValueError, TypeError):
        raise HTTPException(422, f"Fecha inválida '{s}': usar formato YYYY-MM-DD")


def _out(c: models.Compra, nombres: dict[int, str] | None = None) -> schemas.CompraOut:
    o = schemas.CompraOut.model_validate(c)
    o.proveedor_nombre = c.proveedor.nombre if c.proveedor else ""
    o.entregada = c.fecha_entrega is not None
    det_out = []
    for d in (c.detalles or []):
        od = schemas.DetalleCompraOut.model_validate(d)
        od.producto_nombre = (nombres or {}).get(d.producto_id, "")
        det_out.append(od)
    o.detalles = det_out
    pagos = []
    total_pagado = money(0)
    total_desc = money(0)
    for p in (c.pagos or []):
        total_aplicado = money(p.monto + p.descuento)
        po = schemas.PagoCompraOut.model_validate(p)
        po.total_aplicado = float(total_aplicado)
        pagos.append(po)
        total_pagado = money(total_pagado + p.monto)
        total_desc = money(total_desc + p.descuento)
    if not pagos and c.pagado and c.medio_pago:
        pagos = [schemas.PagoCompraOut(id=0, fecha=None, medio=c.medio_pago, monto=float(c.monto), descuento=0, total_aplicado=float(c.monto), legado=True)]
        total_pagado = money(c.monto)
    o.pagos = pagos
    o.total_pagado = float(total_pagado)
    o.total_descuentos = float(total_desc)
    saldo_pendiente = money(0) if c.pagado and not c.pagos else money(max(money(0), c.monto - sum((p.monto + p.descuento for p in (c.pagos or [])), money(0))))
    o.saldo_pendiente = float(saldo_pendiente)
    dias = getattr(c.proveedor, "pronto_pago_dias", None)
    porcentaje = getattr(c.proveedor, "pronto_pago_porcentaje", None)
    if dias is not None and porcentaje is not None and porcentaje > 0:
        limite = c.fecha_pedido.date() + timedelta(days=dias)
        if utc_now().date() <= limite and saldo_pendiente > 0:
            o.sugerencia_pronto_pago = float(money(saldo_pendiente * money(porcentaje) / money(100)))
    return o


def _nombres(db: Session, compras: list[models.Compra]) -> dict[int, str]:
    ids = {d.producto_id for c in compras for d in (c.detalles or [])}
    if not ids:
        return {}
    return {p.id: p.nombre for p in db.query(models.Producto).filter(models.Producto.id.in_(ids)).all()}



def _q_base(db: Session):
    return db.query(models.Compra).options(
        joinedload(models.Compra.proveedor),
        joinedload(models.Compra.detalles),
        joinedload(models.Compra.pagos))


@router.post("", response_model=schemas.CompraOut, status_code=201, dependencies=[leer])
def crear(d: schemas.CompraCreate, db: Session = Depends(get_db)):
    try:
        compra = purchase_service.crear_compra(db, d)
    except purchase_service.PurchaseError as e:
        db.rollback()
        raise HTTPException(e.status_code, e.detail)
    compra = _q_base(db).filter(models.Compra.id == compra.id).first()
    return _out(compra, _nombres(db, [compra]))

@router.get("", response_model=list[schemas.CompraOut], dependencies=[leer])
def listar(fecha: str | None = None, proveedor: int | None = None,
           pagada: bool | None = None, entregada: bool | None = None,
           db: Session = Depends(get_db)):
    q = _q_base(db)
    if fecha:
        ini, fin = local_day_bounds_utc(_parse_fecha(fecha))
        q = q.filter(models.Compra.fecha_pedido >= ini,
                     models.Compra.fecha_pedido < fin)
    if proveedor:
        q = q.filter(models.Compra.proveedor_id == proveedor)
    if pagada is not None:
        q = q.filter(models.Compra.pagado == pagada)
    if entregada is not None:
        if entregada:
            q = q.filter(models.Compra.fecha_entrega.is_not(None))
        else:
            q = q.filter(models.Compra.fecha_entrega.is_(None))
    comps = q.order_by(models.Compra.fecha_pedido.desc()).all()
    nom = _nombres(db, comps)
    return [_out(c, nom) for c in comps]


@router.get("/deudas", dependencies=[leer])
def deudas(db: Session = Depends(get_db)):
    """Deuda actual por distribuidora = suma de compras impagas."""
    res = []
    for pr in db.query(models.Proveedor).order_by(models.Proveedor.nombre).all():
        compras = db.query(models.Compra).filter(models.Compra.proveedor_id == pr.id).all()
        deuda = money(0)
        pendientes = 0
        for c in compras:
            aplicado = money(sum((p.monto + p.descuento for p in (c.pagos or [])), money(0)))
            saldo = money(0) if c.pagado and not c.pagos else money(max(money(0), c.monto - aplicado))
            if saldo > 0:
                deuda = money(deuda + saldo)
                pendientes += 1
        res.append({"id": pr.id, "nombre": pr.nombre, "alias": pr.alias,
                    "dias_entrega": pr.dias_entrega,
                    "deuda": deuda,
                    "pendientes": pendientes,
                    "pronto_pago_dias": pr.pronto_pago_dias,
                    "pronto_pago_porcentaje": pr.pronto_pago_porcentaje})
    return res


@router.get("/{cid}", response_model=schemas.CompraOut, dependencies=[leer])
def obtener(cid: int, db: Session = Depends(get_db)):
    c = _q_base(db).filter(models.Compra.id == cid).first()
    if not c:
        raise HTTPException(404, "Compra no encontrada")
    return _out(c, _nombres(db, [c]))


@router.patch("/{cid}", response_model=schemas.CompraOut, dependencies=[leer])
def actualizar(cid: int, d: schemas.CompraUpdate, db: Session = Depends(get_db)):
    try:
        compra = purchase_service.actualizar_compra(db, cid, d)
    except purchase_service.PurchaseError as e:
        db.rollback()
        raise HTTPException(e.status_code, e.detail)
    compra = _q_base(db).filter(models.Compra.id == compra.id).first()
    return _out(compra, _nombres(db, [compra]))


@router.patch("/{cid}/entregar", response_model=schemas.CompraOut, dependencies=[leer])
def entregar(cid: int, db: Session = Depends(get_db)):
    try:
        compra = purchase_service.entregar_compra(db, cid)
    except purchase_service.PurchaseError as e:
        db.rollback()
        raise HTTPException(e.status_code, e.detail)
    compra = _q_base(db).filter(models.Compra.id == compra.id).first()
    return _out(compra, _nombres(db, [compra]))


@router.patch("/{cid}/pagar", response_model=schemas.CompraOut, dependencies=[leer])
def pagar(cid: int, d: schemas.PagoCompraIn, db: Session = Depends(get_db)):
    try:
        compra = purchase_service.pagar_compra(db, cid, d.model_dump())
    except purchase_service.PurchaseError as e:
        db.rollback()
        raise HTTPException(e.status_code, e.detail)
    compra = _q_base(db).filter(models.Compra.id == compra.id).first()
    return _out(compra, _nombres(db, [compra]))


@router.delete("/{cid}", status_code=204, dependencies=[leer])
def eliminar(cid: int, db: Session = Depends(get_db)):
    try:
        purchase_service.eliminar_compra(db, cid)
    except purchase_service.PurchaseError as e:
        db.rollback()
        raise HTTPException(e.status_code, e.detail)
    return None
