"""Helper assertions for domain invariants."""
from sqlalchemy.orm import Session
from app import models


def assert_stock_movement(
    session: Session,
    producto_id: int,
    tipo: models.TipoMovimiento,
    cantidad: int,
    stock_anterior: int,
    stock_nuevo: int,
    pedido_id: int | None = None,
    compra_id: int | None = None,
) -> models.MovimientoStock:
    """Assert a MovimientoStock exists with exact matching fields."""
    q = session.query(models.MovimientoStock).filter(
        models.MovimientoStock.producto_id == producto_id,
        models.MovimientoStock.tipo == tipo,
        models.MovimientoStock.cantidad == cantidad,
        models.MovimientoStock.stock_anterior == stock_anterior,
        models.MovimientoStock.stock_nuevo == stock_nuevo,
    )
    if pedido_id is not None:
        q = q.filter(models.MovimientoStock.pedido_id == pedido_id)
    if compra_id is not None:
        q = q.filter(models.MovimientoStock.compra_id == compra_id)

    mov = q.first()
    if not mov:
        filters = f"producto_id={producto_id}, tipo={tipo.value}, cantidad={cantidad}, stock_anterior={stock_anterior}, stock_nuevo={stock_nuevo}"
        if pedido_id:
            filters += f", pedido_id={pedido_id}"
        if compra_id:
            filters += f", compra_id={compra_id}"
        raise AssertionError(f"MovimientoStock no encontrado con: {filters}")
    return mov


def assert_caja_movement(
    session: Session,
    tipo: models.TipoMovCaja,
    medio: models.MetodoPago,
    descripcion_contains: str,
    monto: float,
    pedido_id: int | None = None,
    compra_id: int | None = None,
) -> models.MovimientoCaja:
    """Assert a MovimientoCaja exists with matching fields."""
    q = session.query(models.MovimientoCaja).filter(
        models.MovimientoCaja.tipo == tipo,
        models.MovimientoCaja.medio == medio,
        models.MovimientoCaja.monto == monto,
    )
    if descripcion_contains:
        q = q.filter(models.MovimientoCaja.descripcion.contains(descripcion_contains))
    if pedido_id is not None:
        q = q.filter(models.MovimientoCaja.pedido_id == pedido_id)
    if compra_id is not None:
        q = q.filter(models.MovimientoCaja.compra_id == compra_id)

    mov = q.first()
    if not mov:
        filters = f"tipo={tipo.value}, medio={medio.value}, monto={monto}"
        if descripcion_contains:
            filters += f", descripcion contiene '{descripcion_contains}'"
        if pedido_id:
            filters += f", pedido_id={pedido_id}"
        if compra_id:
            filters += f", compra_id={compra_id}"
        raise AssertionError(f"MovimientoCaja no encontrado con: {filters}")
    return mov


def assert_producto_stock(session: Session, producto_id: int, expected: int):
    """Assert producto.stock equals expected."""
    prod = session.get(models.Producto, producto_id)
    if not prod:
        raise AssertionError(f"Producto {producto_id} no existe")
    if prod.stock != expected:
        raise AssertionError(f"Stock mismatch: esperado {expected}, actual {prod.stock}")


def assert_pedido_totals(
    pedido: models.Pedido,
    line_items: list[dict],
    order_descuento_tipo: models.TipoDescuento,
    order_descuento_valor: float,
):
    """Assert pedido subtotal and total match calculated values using aplicar_descuento."""
    from app.services.discounts import aplicar_descuento

    subtotal = 0.0
    for item in line_items:
        base = round(item["producto"].precio_venta * item["cantidad"], 2)
        sub_linea = aplicar_descuento(base, item.get("descuento_tipo", models.TipoDescuento.ningun).value, item.get("descuento_valor", 0))
        subtotal = round(subtotal + sub_linea, 2)

    if abs(pedido.subtotal - subtotal) > 0.01:
        raise AssertionError(f"Subtotal mismatch: esperado {subtotal}, actual {pedido.subtotal}")

    total = aplicar_descuento(subtotal, order_descuento_tipo.value, order_descuento_valor)
    if abs(pedido.total - total) > 0.01:
        raise AssertionError(f"Total mismatch: esperado {total}, actual {pedido.total}")


def assert_proveedor_saldo(session: Session, proveedor_id: int, expected: float):
    """Assert proveedor running saldo equals expected."""
    SIGNO_DEUDA = {
        models.TipoMovProveedor.BOLETA_001: 1,
        models.TipoMovProveedor.PAGO_EFECTIVO_002: -1,
        models.TipoMovProveedor.PAGO_TRANSFER_003: -1,
        models.TipoMovProveedor.NOTA_CREDITO_004: -1,
    }
    movs = session.query(models.MovimientoProveedor).filter(
        models.MovimientoProveedor.proveedor_id == proveedor_id
    ).all()
    saldo = round(sum(SIGNO_DEUDA[m.tipo] * m.monto for m in movs), 2)
    if abs(saldo - expected) > 0.01:
        raise AssertionError(f"Saldo proveedor {proveedor_id} mismatch: esperado {expected}, actual {saldo}")