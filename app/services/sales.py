"""Casos de uso de ventas.

La capa HTTP queda en `routers/orders.py`; aquí se conserva la transacción
completa de crear/cancelar una venta para que stock, pagos y caja sean
atómicos entre sí.
"""

from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.services.discounts import aplicar_descuento
from app.services import stock as stock_service
from app.services import cash as cash_service
from app.services.money import money
from app.core.time import utc_now


class SalesError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _lock_producto(db: Session, producto_id: int) -> models.Producto | None:
    q = db.query(models.Producto).filter(models.Producto.id == producto_id)
    try:
        if db.get_bind().dialect.name == "postgresql":
            q = q.with_for_update()
    except Exception:
        pass
    return q.first()


def _medio_dominante(
    pagos: list[tuple[models.MetodoPago, float]],
) -> models.MetodoPago:
    dom, top = pagos[0][0], pagos[0][1]
    for metodo, monto in pagos[1:]:
        if monto > top:
            dom, top = metodo, monto
    return dom


def crear_venta(db: Session, data: schemas.PedidoCreate) -> models.Pedido:
    cliente = db.get(models.Cliente, data.cliente_id)
    if not cliente:
        raise SalesError(404, "Cliente no existe")

    detalles_db: list[models.DetallePedido] = []
    movimientos: list[models.MovimientoStock] = []
    subtotal = money(0)

    for item in data.detalles:
        producto = _lock_producto(db, item.producto_id)
        if not producto:
            raise SalesError(404, f"Producto {item.producto_id} no existe")
        if not producto.activo:
            raise SalesError(422, f"Producto '{producto.nombre}' esta inactivo y no se puede vender")
        if producto.precio_venta <= 0:
            raise SalesError(422, f"Producto '{producto.nombre}' tiene precio 0, no vendible")
        if producto.stock <= 0:
            raise SalesError(422, f"Producto '{producto.nombre}' sin stock")
        if item.cantidad > producto.stock:
            raise SalesError(
                422,
                f"Stock insuficiente para '{producto.nombre}': pedido {item.cantidad}, disponible {producto.stock}",
            )

        base = money(producto.precio_venta * item.cantidad)
        try:
            subtotal_linea = aplicar_descuento(
                base, item.descuento_tipo.value, item.descuento_valor
            )
        except ValueError as e:
            raise SalesError(422, f"Descuento linea {producto.nombre}: {e}")
        subtotal = money(subtotal + subtotal_linea)

        try:
            movimientos.append(
                stock_service.egresar_venta(db, producto, item.cantidad)
            )
        except stock_service.StockError as e:
            raise SalesError(422, str(e))

        detalles_db.append(
            models.DetallePedido(
                producto_id=producto.id,
                cantidad=item.cantidad,
                precio_unitario=producto.precio_venta,
                nombre_snapshot=producto.nombre,
                descuento_tipo=item.descuento_tipo,
                descuento_valor=item.descuento_valor,
                subtotal_linea=subtotal_linea,
            )
        )

    try:
        total = aplicar_descuento(
            subtotal, data.descuento_tipo.value, data.descuento_valor
        )
    except ValueError as e:
        raise SalesError(422, f"Descuento pedido: {e}")

    if data.pagos is None:
        pagos_norm: list[tuple[models.MetodoPago, object]] = [
            (data.metodo_pago, total)
        ]
    else:
        pagos_norm = [(p.metodo, money(p.monto)) for p in data.pagos]
        suma = money(sum((monto for _, monto in pagos_norm), money(0)))
        if abs(suma - total) > money("0.01"):
            diferencia = money(total - suma)
            if diferencia > 0:
                raise SalesError(
                    422,
                    f"Pagos no cuadran con el total ${total:.2f}: faltan ${diferencia:.2f}",
                )
            raise SalesError(
                422,
                f"Pagos no cuadran con el total ${total:.2f}: sobran ${abs(diferencia):.2f}",
            )

    pedido = models.Pedido(
        cliente_id=data.cliente_id,
        fecha=utc_now(),
        estado=models.EstadoPedido.pagado,
        metodo_pago=_medio_dominante(pagos_norm),
        moneda="ARS",
        descuento_tipo=data.descuento_tipo,
        descuento_valor=data.descuento_valor,
        subtotal=subtotal,
        total=total,
        detalles=detalles_db,
        pagos=[
            models.PagoPedido(metodo=metodo, monto=monto)
            for metodo, monto in pagos_norm
        ],
    )
    db.add(pedido)
    db.flush()

    for movimiento in movimientos:
        movimiento.pedido_id = pedido.id

    for metodo, monto in pagos_norm:
        cash_service.registrar(
            db,
            tipo=models.TipoMovCaja.ENTRADA,
            medio=metodo,
            descripcion=f"Venta #{pedido.id} · {cliente.nombre} ({metodo.value})",
            monto=monto,
            pedido_id=pedido.id,
        )

    db.commit()
    return (
        db.query(models.Pedido)
        .options(
            joinedload(models.Pedido.detalles),
            joinedload(models.Pedido.pagos),
        )
        .filter(models.Pedido.id == pedido.id)
        .first()
    )


def cancelar_venta(db: Session, pedido_id: int) -> models.Pedido:
    pedido = (
        db.query(models.Pedido)
        .options(
            joinedload(models.Pedido.detalles),
            joinedload(models.Pedido.pagos),
        )
        .filter(models.Pedido.id == pedido_id)
        .first()
    )
    if not pedido:
        raise SalesError(404, "Pedido no encontrado")
    if pedido.estado == models.EstadoPedido.cancelado:
        raise SalesError(400, "Pedido ya cancelado")

    pagos_origen = (
        [(p.metodo, p.monto) for p in pedido.pagos]
        if pedido.pagos
        else [(pedido.metodo_pago, pedido.total)]
    )

    for detalle in pedido.detalles:
        producto = _lock_producto(db, detalle.producto_id)
        if not producto:
            raise SalesError(
                404, f"Producto {detalle.producto_id} del pedido no existe"
            )
        try:
            stock_service.devolver_cancelacion(
                db, producto, detalle.cantidad, pedido_id=pedido.id
            )
        except stock_service.StockError as e:
            raise SalesError(422, str(e))

    pedido.estado = models.EstadoPedido.cancelado
    for metodo, monto in pagos_origen:
        cash_service.registrar(
            db,
            tipo=models.TipoMovCaja.SALIDA,
            medio=metodo,
            descripcion=f"Anulación venta #{pedido.id} ({metodo.value})",
            monto=monto,
            pedido_id=pedido.id,
        )

    db.commit()
    return (
        db.query(models.Pedido)
        .options(
            joinedload(models.Pedido.detalles),
            joinedload(models.Pedido.pagos),
        )
        .filter(models.Pedido.id == pedido_id)
        .first()
    )
