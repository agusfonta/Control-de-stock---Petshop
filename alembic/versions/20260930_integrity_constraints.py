"""Restricciones de integridad en base de datos.

Revision ID: 20260930_integrity_constraints
Revises: 20260930_business_requests
"""
from alembic import op

revision = "20260930_integrity_constraints"
down_revision = "20260930_business_requests"
branch_labels = None
depends_on = None


CHECKS = [
    ("productos", "ck_productos_precio_costo_nonnegative", "precio_costo >= 0"),
    ("productos", "ck_productos_precio_venta_nonnegative", "precio_venta >= 0"),
    ("productos", "ck_productos_stock_nonnegative", "stock >= 0"),
    ("productos", "ck_productos_stock_minimo_nonnegative", "stock_minimo >= 0"),
    ("mascotas", "ck_mascotas_nombre_not_blank", "length(trim(nombre)) > 0"),
    ("pedidos", "ck_pedidos_descuento_nonnegative", "descuento_valor >= 0"),
    ("pedidos", "ck_pedidos_descuento_porcentaje_max", "descuento_tipo != 'porcentaje' OR descuento_valor <= 100"),
    ("pedidos", "ck_pedidos_descuento_ningun_zero", "descuento_tipo != 'ningun' OR descuento_valor = 0"),
    ("pedidos", "ck_pedidos_subtotal_nonnegative", "subtotal >= 0"),
    ("pedidos", "ck_pedidos_total_nonnegative", "total >= 0"),
    ("pedidos", "ck_pedidos_total_lte_subtotal", "total <= subtotal"),
    ("pagos_pedido", "ck_pagos_pedido_monto_positive", "monto > 0"),
    ("detalles_pedido", "ck_detalles_pedido_cantidad_positive", "cantidad > 0"),
    ("detalles_pedido", "ck_detalles_pedido_precio_nonnegative", "precio_unitario >= 0"),
    ("detalles_pedido", "ck_detalles_pedido_descuento_nonnegative", "descuento_valor >= 0"),
    ("detalles_pedido", "ck_detalles_pedido_descuento_porcentaje_max", "descuento_tipo != 'porcentaje' OR descuento_valor <= 100"),
    ("detalles_pedido", "ck_detalles_pedido_descuento_ningun_zero", "descuento_tipo != 'ningun' OR descuento_valor = 0"),
    ("detalles_pedido", "ck_detalles_pedido_subtotal_nonnegative", "subtotal_linea >= 0"),
    ("movimientos_stock", "ck_movimientos_stock_cantidad_positive", "cantidad > 0"),
    ("movimientos_stock", "ck_movimientos_stock_anterior_nonnegative", "stock_anterior >= 0"),
    ("movimientos_stock", "ck_movimientos_stock_nuevo_nonnegative", "stock_nuevo >= 0"),
    ("proveedores", "ck_proveedores_pronto_pago_dias_range", "pronto_pago_dias >= 0 AND pronto_pago_dias <= 3650"),
    ("proveedores", "ck_proveedores_pronto_pago_porcentaje_range", "pronto_pago_porcentaje >= 0 AND pronto_pago_porcentaje <= 100"),
    ("movimientos_proveedor", "ck_movimientos_proveedor_monto_positive", "monto > 0"),
    ("movimientos_caja", "ck_movimientos_caja_monto_positive", "monto > 0"),
    ("compras", "ck_compras_monto_nonnegative", "monto >= 0"),
    ("detalles_compra", "ck_detalles_compra_cantidad_positive", "cantidad > 0"),
    ("detalles_compra", "ck_detalles_compra_costo_nonnegative", "costo_unitario >= 0"),
    ("detalles_compra", "ck_detalles_compra_subtotal_nonnegative", "subtotal >= 0"),
    ("pagos_compra", "ck_pagos_compra_monto_nonnegative", "monto >= 0"),
    ("pagos_compra", "ck_pagos_compra_descuento_nonnegative", "descuento >= 0"),
    ("pagos_compra", "ck_pagos_compra_aplicado_positive", "monto + descuento > 0"),
    ("configuracion", "ck_configuracion_margen_range", "margen_venta_porcentaje >= 0 AND margen_venta_porcentaje <= 1000"),
    ("users", "ck_users_rol_valid", "rol IN ('admin', 'vendedor')"),
]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        by_table = {}
        for table, name, condition in CHECKS:
            by_table.setdefault(table, []).append((name, condition))
        for table, constraints in by_table.items():
            with op.batch_alter_table(table, recreate="always") as batch_op:
                for name, condition in constraints:
                    batch_op.create_check_constraint(name, condition)
    else:
        for table, name, condition in CHECKS:
            op.create_check_constraint(name, table, condition)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        by_table = {}
        for table, name, _ in CHECKS:
            by_table.setdefault(table, []).append(name)
        for table, names in by_table.items():
            with op.batch_alter_table(table, recreate="always") as batch_op:
                for name in reversed(names):
                    batch_op.drop_constraint(name, type_="check")
    else:
        for table, name, _ in reversed(CHECKS):
            op.drop_constraint(name, table, type_="check")
