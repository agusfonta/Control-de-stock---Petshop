"""Cambios de negocio: mascotas, pagos parciales, QR, margen y vendedora.

Revision ID: 20260930_business_requests
Revises: 20260930_money_numeric
"""
from alembic import op
import sqlalchemy as sa

revision = "20260930_business_requests"
down_revision = "7f2b8d5c4e31"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE metodopago ADD VALUE IF NOT EXISTS 'qr'")

    op.create_table(
        "mascotas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("especie", sa.Enum("perro", "gato", name="especiemascota"), nullable=False),
        sa.Column("nombre", sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mascotas_cliente_id"), "mascotas", ["cliente_id"], unique=False)

    op.add_column("proveedores", sa.Column("pronto_pago_dias", sa.Integer(), nullable=True))
    op.add_column("proveedores", sa.Column("pronto_pago_porcentaje", sa.Numeric(14, 2), nullable=True))

    op.create_table(
        "pagos_compra",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("compra_id", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.DateTime(), nullable=True),
        sa.Column("medio", sa.Enum("efectivo", "tarjeta", "qr", "transferencia", "mercadopago", "debito", "credito", name="metodopago", create_type=False), nullable=False),
        sa.Column("monto", sa.Numeric(14, 2), nullable=False),
        sa.Column("descuento", sa.Numeric(14, 2), nullable=False),
        sa.ForeignKeyConstraint(["compra_id"], ["compras.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pagos_compra_compra_id"), "pagos_compra", ["compra_id"], unique=False)

    with op.batch_alter_table("pedidos") as batch:
        batch.add_column(sa.Column("vendedora_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_pedidos_vendedora_id", "users", ["vendedora_id"], ["id"], ondelete="SET NULL")
        batch.create_index(op.f("ix_pedidos_vendedora_id"), ["vendedora_id"], unique=False)

    op.create_table(
        "configuracion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("margen_venta_porcentaje", sa.Numeric(8, 2), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("INSERT INTO configuracion (id, margen_venta_porcentaje) VALUES (1, 0)")


def downgrade():
    with op.batch_alter_table("pedidos") as batch:
        batch.drop_index(op.f("ix_pedidos_vendedora_id"))
        batch.drop_constraint("fk_pedidos_vendedora_id", type_="foreignkey")
        batch.drop_column("vendedora_id")
    op.drop_table("configuracion")
    op.drop_index(op.f("ix_pagos_compra_compra_id"), table_name="pagos_compra")
    op.drop_table("pagos_compra")
    op.drop_column("proveedores", "pronto_pago_porcentaje")
    op.drop_column("proveedores", "pronto_pago_dias")
    op.drop_index(op.f("ix_mascotas_cliente_id"), table_name="mascotas")
    op.drop_table("mascotas")
    # PostgreSQL enum values are intentionally not removed in downgrade.
