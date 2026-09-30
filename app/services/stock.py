"""Operaciones de stock y su auditoría.

Las funciones no hacen commit: el router/servicio que inicia la operación
mantiene la transacción completa (venta, compra, etc.).
"""
from datetime import datetime

from app import models
from app.core.time import utc_now


class StockError(ValueError):
    """Error de una operación de stock que debe impedir la transacción."""


def _registrar(
    db,
    producto: models.Producto,
    delta: int,
    tipo: models.TipoMovimiento,
    *,
    pedido_id: int | None = None,
    compra_id: int | None = None,
    fecha: datetime | None = None,
):
    if delta == 0:
        return None
    nuevo = producto.stock + delta
    if nuevo < 0:
        raise StockError(
            f"Stock insuficiente para '{producto.nombre}': se intentó dejarlo en {nuevo}."
        )

    anterior = producto.stock
    producto.stock = nuevo
    movimiento = models.MovimientoStock(
        producto_id=producto.id,
        tipo=tipo,
        cantidad=abs(delta),
        stock_anterior=anterior,
        stock_nuevo=nuevo,
        pedido_id=pedido_id,
        compra_id=compra_id,
        fecha=fecha or utc_now(),
    )
    db.add(movimiento)
    return movimiento


def ingresar(
    db,
    producto: models.Producto,
    cantidad: int,
    *,
    compra_id: int | None = None,
    fecha: datetime | None = None,
    tipo: models.TipoMovimiento = models.TipoMovimiento.INGRESO,
):
    if cantidad <= 0:
        raise StockError("La cantidad de ingreso debe ser mayor a 0.")
    return _registrar(
        db, producto, cantidad, tipo, compra_id=compra_id, fecha=fecha
    )


def egresar_venta(
    db,
    producto: models.Producto,
    cantidad: int,
    *,
    pedido_id: int | None = None,
    fecha: datetime | None = None,
):
    if cantidad <= 0:
        raise StockError("La cantidad de venta debe ser mayor a 0.")
    return _registrar(
        db,
        producto,
        -cantidad,
        models.TipoMovimiento.EGRESO_VENTA,
        pedido_id=pedido_id,
        fecha=fecha,
    )


def devolver_cancelacion(
    db,
    producto: models.Producto,
    cantidad: int,
    *,
    pedido_id: int | None = None,
    fecha: datetime | None = None,
):
    if cantidad <= 0:
        raise StockError("La cantidad de devolución debe ser mayor a 0.")
    return _registrar(
        db,
        producto,
        cantidad,
        models.TipoMovimiento.DEVOLUCION_CANCEL,
        pedido_id=pedido_id,
        fecha=fecha,
    )


def ajustar(
    db,
    producto: models.Producto,
    stock_nuevo: int,
    *,
    fecha: datetime | None = None,
):
    if stock_nuevo < 0:
        raise StockError("El stock no puede ser negativo.")
    return _registrar(
        db,
        producto,
        stock_nuevo - producto.stock,
        models.TipoMovimiento.AJUSTE,
        fecha=fecha,
    )
