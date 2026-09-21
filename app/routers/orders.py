from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app import models, schemas
from app.services.discounts import aplicar_descuento
from app.deps import require_roles

router = APIRouter(prefix="/pedidos", tags=["pedidos"])
leer = Depends(require_roles("admin", "vendedor"))

def _parse_fecha(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        raise HTTPException(422, f"Fecha inválida '{s}': usar formato YYYY-MM-DD")

def _lock_productos(db: Session, pid: int) -> models.Producto | None:
    """Bloqueo pesimista en Postgres para evitar ventas concurrentes en negativo."""
    q = db.query(models.Producto).filter(models.Producto.id == pid)
    try:
        if db.get_bind().dialect.name == "postgresql":
            q = q.with_for_update()
    except Exception:
        pass
    return q.first()

@router.post("", response_model=schemas.PedidoOut, status_code=201, dependencies=[leer])
def crear(d: schemas.PedidoCreate, db: Session = Depends(get_db)):
    cli = db.get(models.Cliente, d.cliente_id)
    if not cli:
        raise HTTPException(404, "Cliente no existe")
    try:
        detalles_db: list[models.DetallePedido] = []
        movimientos: list[models.MovimientoStock] = []
        subtotal = 0.0
        # Validar y descontar stock en transacción
        for item in d.detalles:
            p = _lock_productos(db, item.producto_id)
            if not p:
                raise HTTPException(404, f"Producto {item.producto_id} no existe")
            if not p.activo:
                raise HTTPException(422, f"Producto '{p.nombre}' esta inactivo y no se puede vender")
            if p.precio_venta <= 0:
                raise HTTPException(422, f"Producto '{p.nombre}' tiene precio 0, no vendible")
            if p.stock <= 0:
                raise HTTPException(422, f"Producto '{p.nombre}' sin stock")
            if item.cantidad > p.stock:
                raise HTTPException(422, f"Stock insuficiente para '{p.nombre}': pedido {item.cantidad}, disponible {p.stock}")
            base = round(p.precio_venta * item.cantidad, 2)
            try:
                sub_linea = aplicar_descuento(base, item.descuento_tipo.value, item.descuento_valor)
            except ValueError as e:
                raise HTTPException(422, f"Descuento linea {p.nombre}: {e}")
            subtotal = round(subtotal + sub_linea, 2)
            ant = p.stock
            p.stock = ant - item.cantidad
            movimientos.append(models.MovimientoStock(
                producto_id=p.id, tipo=models.TipoMovimiento.EGRESO_VENTA,
                cantidad=item.cantidad, stock_anterior=ant, stock_nuevo=p.stock,
            ))
            detalles_db.append(models.DetallePedido(
                producto_id=p.id, cantidad=item.cantidad,
                precio_unitario=p.precio_venta, nombre_snapshot=p.nombre,
                descuento_tipo=item.descuento_tipo, descuento_valor=item.descuento_valor,
                subtotal_linea=sub_linea,
            ))
        try:
            total = aplicar_descuento(subtotal, d.descuento_tipo.value, d.descuento_valor)
        except ValueError as e:
            raise HTTPException(422, f"Descuento pedido: {e}")
        ped = models.Pedido(
            cliente_id=d.cliente_id, fecha=datetime.utcnow(), estado=models.EstadoPedido.pagado,
            metodo_pago=d.metodo_pago, moneda="ARS",
            descuento_tipo=d.descuento_tipo, descuento_valor=d.descuento_valor,
            subtotal=subtotal, total=total, detalles=detalles_db,
        )
        db.add(ped); db.flush()
        for m in movimientos:
            m.pedido_id = ped.id
            db.add(m)
        db.commit(); db.refresh(ped)
        return ped
    except HTTPException:
        db.rollback()
        raise

@router.get("", response_model=list[schemas.PedidoOut], dependencies=[leer])
def listar(fecha: str | None = None, desde: str | None = None, hasta: str | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Pedido).options(joinedload(models.Pedido.detalles))
    if fecha:
        ini = _parse_fecha(fecha)
        q = q.filter(models.Pedido.fecha >= ini, models.Pedido.fecha < ini + timedelta(days=1))
    if desde:
        q = q.filter(models.Pedido.fecha >= _parse_fecha(desde))
    if hasta:
        q = q.filter(models.Pedido.fecha < _parse_fecha(hasta) + timedelta(days=1))
    return q.order_by(models.Pedido.fecha.desc()).all()

@router.get("/{pid}", response_model=schemas.PedidoOut, dependencies=[leer])
def obtener(pid: int, db: Session = Depends(get_db)):
    p = db.query(models.Pedido).options(joinedload(models.Pedido.detalles)).filter(models.Pedido.id == pid).first()
    if not p: raise HTTPException(404, "Pedido no encontrado")
    return p

@router.patch("/{pid}/cancelar", response_model=schemas.PedidoOut, dependencies=[leer])
def cancelar(pid: int, db: Session = Depends(get_db)):
    p = db.query(models.Pedido).options(joinedload(models.Pedido.detalles)).filter(models.Pedido.id == pid).first()
    if not p: raise HTTPException(404, "Pedido no encontrado")
    if p.estado == models.EstadoPedido.cancelado:
        raise HTTPException(400, "Pedido ya cancelado")
    # devolver stock
    for det in p.detalles:
        prod = _lock_productos(db, det.producto_id)
        if not prod:
            db.rollback()
            raise HTTPException(404, f"Producto {det.producto_id} del pedido no existe")
        ant = prod.stock
        prod.stock = ant + det.cantidad
        db.add(models.MovimientoStock(
            producto_id=prod.id, tipo=models.TipoMovimiento.DEVOLUCION_CANCEL,
            cantidad=det.cantidad, stock_anterior=ant, stock_nuevo=prod.stock, pedido_id=p.id,
        ))
    p.estado = models.EstadoPedido.cancelado
    db.commit(); db.refresh(p)
    return p
