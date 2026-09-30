from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app import models, schemas
from app.deps import require_roles
from app.services import purchases as purchase_service
from app.core.time import local_day_bounds_utc
from app.services.money import money

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
    return o


def _nombres(db: Session, compras: list[models.Compra]) -> dict[int, str]:
    ids = {d.producto_id for c in compras for d in (c.detalles or [])}
    if not ids:
        return {}
    return {p.id: p.nombre for p in db.query(models.Producto).filter(models.Producto.id.in_(ids)).all()}



def _q_base(db: Session):
    return db.query(models.Compra).options(
        joinedload(models.Compra.proveedor),
        joinedload(models.Compra.detalles))


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
        impagas = db.query(models.Compra).filter(
            models.Compra.proveedor_id == pr.id,
            models.Compra.pagado == False).all()  # noqa
        res.append({"id": pr.id, "nombre": pr.nombre, "alias": pr.alias,
                    "dias_entrega": pr.dias_entrega,
                    "deuda": money(sum((c.monto for c in impagas), money(0))),
                    "pendientes": len(impagas)})
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
def pagar(cid: int, d: dict, db: Session = Depends(get_db)):
    try:
        compra = purchase_service.pagar_compra(db, cid, d)
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
