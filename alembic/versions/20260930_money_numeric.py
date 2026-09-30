"""Use NUMERIC for monetary columns.

Revision ID: 7f2b8d5c4e31
Revises: 1125afc8e1ed
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7f2b8d5c4e31"
down_revision: Union[str, Sequence[str], None] = "1125afc8e1ed"
branch_labels = None
depends_on = None


MONEY_COLUMNS = {
    "productos": ("precio_costo", "precio_venta"),
    "pedidos": ("descuento_valor", "subtotal", "total"),
    "pagos_pedido": ("monto",),
    "detalles_pedido": ("precio_unitario", "descuento_valor", "subtotal_linea"),
    "movimientos_proveedor": ("monto",),
    "movimientos_caja": ("monto",),
    "compras": ("monto",),
    "detalles_compra": ("costo_unitario", "subtotal"),
}


def upgrade() -> None:
    for table_name, columns in MONEY_COLUMNS.items():
        with op.batch_alter_table(table_name) as batch_op:
            for column_name in columns:
                batch_op.alter_column(
                    column_name,
                    existing_type=sa.Float(),
                    type_=sa.Numeric(14, 2),
                    existing_nullable=False,
                )


def downgrade() -> None:
    for table_name, columns in reversed(list(MONEY_COLUMNS.items())):
        with op.batch_alter_table(table_name) as batch_op:
            for column_name in columns:
                batch_op.alter_column(
                    column_name,
                    existing_type=sa.Numeric(14, 2),
                    type_=sa.Float(),
                    existing_nullable=False,
                )
