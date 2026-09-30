"""Modelos SQLAlchemy - PetShop."""
from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, Table, Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.time import utc_now
import enum


class Unidad(str, enum.Enum):
    unidad = "unidad"
    kg = "kg"
    lt = "lt"
    pack = "pack"


class EstadoPedido(str, enum.Enum):
    pagado = "pagado"
    cancelado = "cancelado"


class MetodoPago(str, enum.Enum):
    efectivo = "efectivo"
    tarjeta = "tarjeta"  # legacy, se conserva por compatibilidad
    qr = "qr"
    transferencia = "transferencia"  # legacy, reemplazado por QR en nuevos registros
    mercadopago = "mercadopago"  # legacy, reemplazado por QR en nuevos registros
    debito = "debito"
    credito = "credito"


class TipoDescuento(str, enum.Enum):
    ningun = "ningun"
    porcentaje = "porcentaje"
    monto_fijo = "monto_fijo"


class EspecieMascota(str, enum.Enum):
    perro = "perro"
    gato = "gato"


class TipoMovimiento(str, enum.Enum):
    INGRESO = "INGRESO"
    EGRESO_VENTA = "EGRESO_VENTA"
    AJUSTE = "AJUSTE"
    DEVOLUCION_CANCEL = "DEVOLUCION_CANCEL"


class TipoMovProveedor(str, enum.Enum):
    """Códigos de la planilla Distribuidoras: 001 pedido/boleta, 002/003 pagos, 004 nota de crédito."""
    BOLETA_001 = "BOLETA_001"
    PAGO_EFECTIVO_002 = "PAGO_EFECTIVO_002"
    PAGO_TRANSFER_003 = "PAGO_TRANSFER_003"
    NOTA_CREDITO_004 = "NOTA_CREDITO_004"


class TipoMovCaja(str, enum.Enum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"


producto_categoria = Table(
    "producto_categoria",
    Base.metadata,
    Column("producto_id", ForeignKey("productos.id", ondelete="CASCADE"), primary_key=True),
    Column("categoria_id", ForeignKey("categorias.id", ondelete="CASCADE"), primary_key=True),
)


producto_proveedor = Table(
    "producto_proveedor",
    Base.metadata,
    Column("producto_id", ForeignKey("productos.id", ondelete="CASCADE"), primary_key=True),
    Column("proveedor_id", ForeignKey("proveedores.id", ondelete="CASCADE"), primary_key=True),
)


class Categoria(Base):
    __tablename__ = "categorias"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(80), unique=True, nullable=False, index=True)
    descripcion = Column(Text, nullable=True)
    productos = relationship("Producto", secondary=producto_categoria, back_populates="categorias")


class Producto(Base):
    __tablename__ = "productos"
    __table_args__ = (
        CheckConstraint("precio_costo >= 0", name="ck_productos_precio_costo_nonnegative"),
        CheckConstraint("precio_venta >= 0", name="ck_productos_precio_venta_nonnegative"),
        CheckConstraint("stock >= 0", name="ck_productos_stock_nonnegative"),
        CheckConstraint("stock_minimo >= 0", name="ck_productos_stock_minimo_nonnegative"),
    )
    id = Column(Integer, primary_key=True)
    sku = Column(String(60), unique=True, nullable=True, index=True)
    nombre = Column(String(120), nullable=False, index=True)
    descripcion = Column(Text, nullable=True)
    marca = Column(String(80), nullable=True)
    unidad = Column(Enum(Unidad), nullable=False, default=Unidad.unidad)
    precio_costo = Column(Numeric(14, 2), nullable=False, default=0)
    precio_venta = Column(Numeric(14, 2), nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    stock_minimo = Column(Integer, nullable=False, default=10)
    imagen_url = Column(String(500), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True, index=True)
    categorias = relationship("Categoria", secondary=producto_categoria, back_populates="productos")
    movimientos = relationship("MovimientoStock", back_populates="producto")
    proveedor = relationship("Proveedor", foreign_keys=[proveedor_id])
    proveedores_alt = relationship("Proveedor", secondary=producto_proveedor)


class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(120), nullable=False)
    email = Column(String(160), unique=True, nullable=False, index=True)
    telefono = Column(String(40), nullable=True)
    dni = Column(String(20), unique=True, nullable=False, index=True)
    direccion = Column(String(250), nullable=True)
    pedidos = relationship("Pedido", back_populates="cliente")
    mascotas = relationship("Mascota", back_populates="cliente", cascade="all, delete-orphan")


class Mascota(Base):
    __tablename__ = "mascotas"
    __table_args__ = (
        CheckConstraint("length(trim(nombre)) > 0", name="ck_mascotas_nombre_not_blank"),
    )
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False, index=True)
    especie = Column(Enum(EspecieMascota), nullable=False)
    nombre = Column(String(80), nullable=False)
    cliente = relationship("Cliente", back_populates="mascotas")


class Pedido(Base):
    __tablename__ = "pedidos"
    __table_args__ = (
        CheckConstraint("descuento_valor >= 0", name="ck_pedidos_descuento_nonnegative"),
        CheckConstraint("descuento_tipo != 'porcentaje' OR descuento_valor <= 100", name="ck_pedidos_descuento_porcentaje_max"),
        CheckConstraint("descuento_tipo != 'ningun' OR descuento_valor = 0", name="ck_pedidos_descuento_ningun_zero"),
        CheckConstraint("subtotal >= 0", name="ck_pedidos_subtotal_nonnegative"),
        CheckConstraint("total >= 0", name="ck_pedidos_total_nonnegative"),
        CheckConstraint("total <= subtotal", name="ck_pedidos_total_lte_subtotal"),
    )
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    fecha = Column(DateTime, nullable=False, default=utc_now)
    estado = Column(Enum(EstadoPedido), nullable=False, default=EstadoPedido.pagado)
    metodo_pago = Column(Enum(MetodoPago), nullable=False)
    moneda = Column(String(3), nullable=False, default="ARS")
    descuento_tipo = Column(Enum(TipoDescuento), nullable=False, default=TipoDescuento.ningun)
    descuento_valor = Column(Numeric(14, 2), nullable=False, default=0)
    subtotal = Column(Numeric(14, 2), nullable=False, default=0)
    total = Column(Numeric(14, 2), nullable=False, default=0)
    cliente = relationship("Cliente", back_populates="pedidos")
    detalles = relationship("DetallePedido", back_populates="pedido", cascade="all, delete-orphan")
    pagos = relationship("PagoPedido", back_populates="pedido", cascade="all, delete-orphan")
    vendedora_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    vendedora = relationship("User", foreign_keys=[vendedora_id])


class PagoPedido(Base):
    """Desglose de medios de pago de una venta (uno o varios por pedido)."""
    __tablename__ = "pagos_pedido"
    __table_args__ = (
        CheckConstraint("monto > 0", name="ck_pagos_pedido_monto_positive"),
    )
    id = Column(Integer, primary_key=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False, index=True)
    metodo = Column(Enum(MetodoPago), nullable=False)
    monto = Column(Numeric(14, 2), nullable=False)
    pedido = relationship("Pedido", back_populates="pagos")


class DetallePedido(Base):
    __tablename__ = "detalles_pedido"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_detalles_pedido_cantidad_positive"),
        CheckConstraint("precio_unitario >= 0", name="ck_detalles_pedido_precio_nonnegative"),
        CheckConstraint("descuento_valor >= 0", name="ck_detalles_pedido_descuento_nonnegative"),
        CheckConstraint("descuento_tipo != 'porcentaje' OR descuento_valor <= 100", name="ck_detalles_pedido_descuento_porcentaje_max"),
        CheckConstraint("descuento_tipo != 'ningun' OR descuento_valor = 0", name="ck_detalles_pedido_descuento_ningun_zero"),
        CheckConstraint("subtotal_linea >= 0", name="ck_detalles_pedido_subtotal_nonnegative"),
    )
    id = Column(Integer, primary_key=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(14, 2), nullable=False)  # snapshot
    nombre_snapshot = Column(String(120), nullable=False)
    descuento_tipo = Column(Enum(TipoDescuento), nullable=False, default=TipoDescuento.ningun)
    descuento_valor = Column(Numeric(14, 2), nullable=False, default=0)
    subtotal_linea = Column(Numeric(14, 2), nullable=False)
    pedido = relationship("Pedido", back_populates="detalles")


class MovimientoStock(Base):
    __tablename__ = "movimientos_stock"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_movimientos_stock_cantidad_positive"),
        CheckConstraint("stock_anterior >= 0", name="ck_movimientos_stock_anterior_nonnegative"),
        CheckConstraint("stock_nuevo >= 0", name="ck_movimientos_stock_nuevo_nonnegative"),
    )
    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    tipo = Column(Enum(TipoMovimiento), nullable=False)
    cantidad = Column(Integer, nullable=False)
    stock_anterior = Column(Integer, nullable=False)
    stock_nuevo = Column(Integer, nullable=False)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=True)
    compra_id = Column(Integer, ForeignKey("compras.id", ondelete="SET NULL"), nullable=True)
    fecha = Column(DateTime, nullable=False, default=utc_now)
    producto = relationship("Producto", back_populates="movimientos")


class Proveedor(Base):
    __tablename__ = "proveedores"
    __table_args__ = (
        CheckConstraint("pronto_pago_dias >= 0 AND pronto_pago_dias <= 3650", name="ck_proveedores_pronto_pago_dias_range"),
        CheckConstraint("pronto_pago_porcentaje >= 0 AND pronto_pago_porcentaje <= 100", name="ck_proveedores_pronto_pago_porcentaje_range"),
    )
    id = Column(Integer, primary_key=True)
    nombre = Column(String(120), nullable=False, unique=True)
    contacto = Column(String(120), nullable=True)
    telefono = Column(String(40), nullable=True)
    alias = Column(String(120), nullable=True)
    dias_entrega = Column(String(120), nullable=True)
    pronto_pago_dias = Column(Integer, nullable=True)
    pronto_pago_porcentaje = Column(Numeric(14, 2), nullable=True)
    movimientos = relationship("MovimientoProveedor", back_populates="proveedor", cascade="all, delete-orphan")


class MovimientoProveedor(Base):
    """Cuenta corriente por distribuidor: boleta 001 suma deuda, pagos 002/003 y N.crédito 004 restan."""
    __tablename__ = "movimientos_proveedor"
    __table_args__ = (
        CheckConstraint("monto > 0", name="ck_movimientos_proveedor_monto_positive"),
    )
    id = Column(Integer, primary_key=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha = Column(DateTime, nullable=False, default=utc_now)
    tipo = Column(Enum(TipoMovProveedor), nullable=False)
    nro = Column(String(60), nullable=False)  # nro boleta; en pagos "PAGO <nro>" o el nro que referencia
    monto = Column(Numeric(14, 2), nullable=False)
    proveedor = relationship("Proveedor", back_populates="movimientos")


class MovimientoCaja(Base):
    """Caja diaria: ENTRADA (ventas auto + extras manuales) y SALIDA (pagos a proveedor auto + gastos manuales)."""
    __tablename__ = "movimientos_caja"
    __table_args__ = (
        CheckConstraint("monto > 0", name="ck_movimientos_caja_monto_positive"),
    )
    id = Column(Integer, primary_key=True)
    fecha = Column(DateTime, nullable=False, default=utc_now, index=True)
    tipo = Column(Enum(TipoMovCaja), nullable=False)
    medio = Column(Enum(MetodoPago), nullable=False)  # EF/MP/DB/CD/TR (+ tarjeta legacy)
    descripcion = Column(String(250), nullable=False)
    monto = Column(Numeric(14, 2), nullable=False)
    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="SET NULL"), nullable=True)
    compra_id = Column(Integer, ForeignKey("compras.id", ondelete="SET NULL"), nullable=True)


class Compra(Base):
    """Pedido a distribuidora: se registra, al entregarse entra stock, al pagarse sale caja."""
    __tablename__ = "compras"
    __table_args__ = (
        CheckConstraint("monto >= 0", name="ck_compras_monto_nonnegative"),
    )
    id = Column(Integer, primary_key=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False, index=True)
    fecha_pedido = Column(DateTime, nullable=False, default=utc_now, index=True)
    nro_boleta = Column(String(60), nullable=False)
    fecha_entrega = Column(DateTime, nullable=True)  # null = "sin entregar"
    pagado = Column(Boolean, nullable=False, default=False)
    medio_pago = Column(Enum(MetodoPago), nullable=True)
    monto = Column(Numeric(14, 2), nullable=False, default=0)  # calculado de las líneas
    proveedor = relationship("Proveedor")
    detalles = relationship("DetalleCompra", back_populates="compra", cascade="all, delete-orphan")
    pagos = relationship("PagoCompra", back_populates="compra", cascade="all, delete-orphan")


class DetalleCompra(Base):
    __tablename__ = "detalles_compra"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_detalles_compra_cantidad_positive"),
        CheckConstraint("costo_unitario >= 0", name="ck_detalles_compra_costo_nonnegative"),
        CheckConstraint("subtotal >= 0", name="ck_detalles_compra_subtotal_nonnegative"),
    )
    id = Column(Integer, primary_key=True)
    compra_id = Column(Integer, ForeignKey("compras.id", ondelete="CASCADE"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    costo_unitario = Column(Numeric(14, 2), nullable=False)  # snapshot (default: precio_costo)
    subtotal = Column(Numeric(14, 2), nullable=False)
    compra = relationship("Compra", back_populates="detalles")


class PagoCompra(Base):
    """Pago individual de una compra. Permite pagos parciales y descuentos aplicados al saldo."""
    __tablename__ = "pagos_compra"
    __table_args__ = (
        CheckConstraint("monto >= 0", name="ck_pagos_compra_monto_nonnegative"),
        CheckConstraint("descuento >= 0", name="ck_pagos_compra_descuento_nonnegative"),
        CheckConstraint("monto + descuento > 0", name="ck_pagos_compra_aplicado_positive"),
    )
    id = Column(Integer, primary_key=True)
    compra_id = Column(Integer, ForeignKey("compras.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha = Column(DateTime, nullable=True, default=utc_now)
    medio = Column(Enum(MetodoPago), nullable=False)
    monto = Column(Numeric(14, 2), nullable=False)
    descuento = Column(Numeric(14, 2), nullable=False, default=0)
    compra = relationship("Compra", back_populates="pagos")


class Configuracion(Base):
    __tablename__ = "configuracion"
    __table_args__ = (
        CheckConstraint("margen_venta_porcentaje >= 0 AND margen_venta_porcentaje <= 1000", name="ck_configuracion_margen_range"),
    )
    id = Column(Integer, primary_key=True)
    margen_venta_porcentaje = Column(Numeric(8, 2), nullable=False, default=0)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("rol IN ('admin', 'vendedor')", name="ck_users_rol_valid"),
    )
    id = Column(Integer, primary_key=True)
    username = Column(String(60), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    rol = Column(String(20), nullable=False, default="vendedor")  # admin | vendedor
    activo = Column(Boolean, nullable=False, default=True)
