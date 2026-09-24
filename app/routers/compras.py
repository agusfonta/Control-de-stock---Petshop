from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app import models, schemas
from app.deps import require_roles

router = APIRouter(prefix="/compras", tags=["compras"])
leer = Depends(require_roles("admin", "vendedor"))


def _parse_fecha(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
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


def _armar_detalles(db: Session, detalles_in: list[schemas.DetalleCompraIn]):
    """Valida líneas y calcula monto. Snapshot de costo = precio_costo salvo override."""
    detalles, monto = [], 0.0
    for item in detalles_in:
        p = db.get(models.Producto, item.producto_id)
        if not p:
            raise HTTPException(404, f"Producto {item.producto_id} no existe")
        costo = item.costo_unitario if item.costo_unitario is not None else (p.precio_costo or 0)
        sub = round(costo * item.cantidad, 2)
        monto = round(monto + sub, 2)
        detalles.append(models.DetalleCompra(
            producto_id=p.id, cantidad=item.cantidad,
            costo_unitario=costo, subtotal=sub))
    if not detalles:
        raise HTTPException(422, "La compra necesita al menos una línea")
    return detalles, monto


def _q_base(db: Session):
    return db.query(models.Compra).options(
        joinedload(models.Compra.proveedor),
        joinedload(models.Compra.detalles))


@router.post("", response_model=schemas.CompraOut, status_code=201, dependencies=[leer])
def crear(d: schemas.CompraCreate, db: Session = Depends(get_db)):
    pr = db.get(models.Proveedor, d.proveedor_id)
    if not pr:
        raise HTTPException(404, "Distribuidora no existe")
    detalles, monto = _armar_detalles(db, d.detalles)
    c = models.Compra(
        proveedor_id=pr.id, nro_boleta=d.nro_boleta.strip(),
        fecha_pedido=d.fecha_pedido or datetime.utcnow(),
        pagado=d.pagado, medio_pago=d.medio_pago,
        monto=monto, detalles=detalles)
    db.add(c); db.flush()
    if d.pagado:
        # pagada al registrar: sale caja en el acto
        db.add(models.MovimientoCaja(
            tipo=models.TipoMovCaja.SALIDA, medio=d.medio_pago,
            descripcion=f"Pago {pr.nombre} {c.nro_boleta}",
            monto=monto, fecha=c.fecha_pedido, compra_id=c.id))
    db.commit(); db.refresh(c)
    _c = _q_base(db).filter(models.Compra.id == c.id).first()
    return _out(_c, _nombres(db, [_c]))


@router.get("", response_model=list[schemas.CompraOut], dependencies=[leer])
def listar(fecha: str | None = None, proveedor: int | None = None,
           pagada: bool | None = None, entregada: bool | None = None,
           db: Session = Depends(get_db)):
    q = _q_base(db)
    if fecha:
        ini = _parse_fecha(fecha)
        q = q.filter(models.Compra.fecha_pedido >= ini,
                     models.Compra.fecha_pedido < ini + timedelta(days=1))
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
                    "deuda": round(sum(c.monto for c in impagas), 2),
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
    c = _q_base(db).filter(models.Compra.id == cid).first()
    if not c:
        raise HTTPException(404, "Compra no encontrada")
    if d.nro_boleta is not None:
        c.nro_boleta = d.nro_boleta.strip()
    if d.fecha_pedido is not None:
        c.fecha_pedido = d.fecha_pedido
    if d.medio_pago is not None:
        c.medio_pago = d.medio_pago
    if d.detalles is not None:
        if c.fecha_entrega is not None:
            raise HTTPException(400, "Ya entregada: las líneas no se pueden editar")
        for old in list(c.detalles):
            db.delete(old)
        db.flush()
        c.detalles, c.monto = _armar_detalles(db, d.detalles)
    db.commit(); db.refresh(c)
    _c = _q_base(db).filter(models.Compra.id == cid).first()
    return _out(_c, _nombres(db, [_c]))


@router.patch("/{cid}/entregar", response_model=schemas.CompraOut, dependencies=[leer])
def entregar(cid: int, db: Session = Depends(get_db)):
    """Marca entregada (hoy) y hace entrar el stock de cada línea."""
    c = _q_base(db).filter(models.Compra.id == cid).first()
    if not c:
        raise HTTPException(404, "Compra no encontrada")
    if c.fecha_entrega is not None:
        raise HTTPException(400, "Ya estaba entregada")
    ahora = datetime.utcnow()
    for det in c.detalles:
        p = db.get(models.Producto, det.producto_id)
        if not p:
            db.rollback()
            raise HTTPException(404, f"Producto {det.producto_id} de la compra no existe")
        ant = p.stock
        p.stock = ant + det.cantidad
        db.add(models.MovimientoStock(
            producto_id=p.id, tipo=models.TipoMovimiento.INGRESO,
            cantidad=det.cantidad, stock_anterior=ant, stock_nuevo=p.stock,
            compra_id=c.id, fecha=ahora))
    c.fecha_entrega = ahora
    db.commit(); db.refresh(c)
    _c = _q_base(db).filter(models.Compra.id == cid).first()
    return _out(_c, _nombres(db, [_c]))


@router.patch("/{cid}/pagar", response_model=schemas.CompraOut, dependencies=[leer])
def pagar(cid: int, d: dict, db: Session = Depends(get_db)):
    """Marca pagada con un medio y registra la salida de caja."""
    c = _q_base(db).filter(models.Compra.id == cid).first()
    if not c:
        raise HTTPException(404, "Compra no encontrada")
    if c.pagado:
        raise HTTPException(400, "Ya estaba pagada")
    medio = (d or {}).get("medio_pago") or (c.medio_pago.value if c.medio_pago else None)
    if not medio:
        raise HTTPException(422, "Indicar medio_pago para pagar")
    try:
        medio_enum = models.MetodoPago(medio)
    except ValueError:
        raise HTTPException(422, f"medio_pago inválido: {medio}")
    c.pagado = True
    c.medio_pago = medio_enum
    db.add(models.MovimientoCaja(
        tipo=models.TipoMovCaja.SALIDA, medio=medio_enum,
        descripcion=f"Pago {c.proveedor.nombre} {c.nro_boleta}",
        monto=c.monto, compra_id=c.id))
    db.commit(); db.refresh(c)
    _c = _q_base(db).filter(models.Compra.id == cid).first()
    return _out(_c, _nombres(db, [_c]))


@router.delete("/{cid}", status_code=204, dependencies=[leer])
def eliminar(cid: int, db: Session = Depends(get_db)):
    c = db.get(models.Compra, cid)
    if not c:
        raise HTTPException(404, "Compra no encontrada")
    if c.fecha_entrega is not None:
        raise HTTPException(400, "Ya entregada: no se puede borrar")
    if c.pagado:
        raise HTTPException(400, "Ya pagada: no se puede borrar")
    db.query(models.MovimientoCaja).filter(models.MovimientoCaja.compra_id == cid).delete()
    db.delete(c); db.commit()
    return None
