"""Pruebas de las restricciones que protege directamente la base de datos."""

import pytest
from sqlalchemy.exc import IntegrityError

from app import models
from tests.factories import create_categoria, create_cliente, create_producto, create_proveedor


def _assert_integrity_error(session, obj):
    session.add(obj)
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_producto_rejects_negative_stock_in_db(session):
    _assert_integrity_error(
        session,
        models.Producto(
            sku="DB-STOCK-NEG",
            nombre="Producto inválido",
            unidad=models.Unidad.unidad,
            precio_costo=100,
            precio_venta=200,
            stock=-1,
            stock_minimo=0,
            activo=True,
        ),
    )


def test_producto_rejects_negative_sale_price_in_db(session):
    _assert_integrity_error(
        session,
        models.Producto(
            sku="DB-PRICE-NEG",
            nombre="Producto precio inválido",
            unidad=models.Unidad.unidad,
            precio_costo=100,
            precio_venta=-1,
            stock=1,
            stock_minimo=0,
            activo=True,
        ),
    )


def test_detalle_pedido_rejects_zero_quantity_in_db(session):
    cli = create_cliente(session, nombre="Cliente DB Pedido")
    cat = create_categoria(session, nombre="Cat DB Pedido")
    prod = create_producto(session, nombre="Prod DB Pedido", categorias=[cat])
    pedido = models.Pedido(
        cliente_id=cli.id,
        metodo_pago=models.MetodoPago.efectivo,
        moneda="ARS",
        descuento_tipo=models.TipoDescuento.ningun,
        descuento_valor=0,
        subtotal=0,
        total=0,
    )
    session.add(pedido)
    session.flush()
    _assert_integrity_error(
        session,
        models.DetallePedido(
            pedido_id=pedido.id,
            producto_id=prod.id,
            cantidad=0,
            precio_unitario=200,
            nombre_snapshot=prod.nombre,
            descuento_tipo=models.TipoDescuento.ningun,
            descuento_valor=0,
            subtotal_linea=0,
        ),
    )


def test_pago_pedido_rejects_non_positive_amount_in_db(session):
    cli = create_cliente(session, nombre="Cliente DB Pago")
    pedido = models.Pedido(
        cliente_id=cli.id,
        metodo_pago=models.MetodoPago.efectivo,
        moneda="ARS",
        descuento_tipo=models.TipoDescuento.ningun,
        descuento_valor=0,
        subtotal=100,
        total=100,
    )
    session.add(pedido)
    session.flush()
    _assert_integrity_error(
        session,
        models.PagoPedido(pedido_id=pedido.id, metodo=models.MetodoPago.efectivo, monto=0),
    )


def test_proveedor_rejects_invalid_pronto_pago_percentage_in_db(session):
    _assert_integrity_error(
        session,
        models.Proveedor(
            nombre="Proveedor DB Margen",
            pronto_pago_dias=7,
            pronto_pago_porcentaje=101,
        ),
    )


def test_movimiento_caja_rejects_non_positive_amount_in_db(session):
    _assert_integrity_error(
        session,
        models.MovimientoCaja(
            tipo=models.TipoMovCaja.ENTRADA,
            medio=models.MetodoPago.efectivo,
            descripcion="Movimiento inválido",
            monto=0,
        ),
    )


def test_pago_compra_rejects_zero_applied_amount_in_db(session):
    prov = create_proveedor(session, nombre="Proveedor DB Pago")
    cat = create_categoria(session, nombre="Cat DB Compra")
    prod = create_producto(session, nombre="Prod DB Compra", categorias=[cat])
    compra = models.Compra(
        proveedor_id=prov.id,
        nro_boleta="DB-001",
        pagado=False,
        monto=200,
    )
    compra.detalles = [
        models.DetalleCompra(
            producto_id=prod.id,
            cantidad=1,
            costo_unitario=200,
            subtotal=200,
        )
    ]
    session.add(compra)
    session.flush()
    _assert_integrity_error(
        session,
        models.PagoCompra(
            compra_id=compra.id,
            medio=models.MetodoPago.efectivo,
            monto=0,
            descuento=0,
        ),
    )


def test_user_rejects_unknown_role_in_db(session):
    _assert_integrity_error(
        session,
        models.User(
            username="db-role-invalid",
            hashed_password="hash",
            rol="admin123",
            activo=True,
        ),
    )
