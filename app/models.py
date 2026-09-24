"""Modelos SQLAlchemy - PetShop."""
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Table, Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
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
    transferencia = "transferencia"
    mercadopago = "mercadopago"
    debito = "debito"
    credito = "credito"


class TipoDescuento(str, enum.Enum):
    ningun = "ningun"
    porcentaje = "porcentaje"
    monto_fijo = "monto_fijo"


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
    id = Column(Integer, primary_key=True)
    sku = Column(String(60), unique=True, nullable=True, index=True)
    nombre = Column(String(120), nullable=False, index=True)
    descripcion = Column(Text, nullable=True)
    marca = Column(String(80), nullable=True)
    unidad = Column(Enum(Unidad), nullable=False, default=Unidad.unidad)
    precio_costo = Column(Float, nullable=False, default=0)
    precio_venta = Column(Float, nullable=False)
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


class Pedido(Base):
    __tablename__ = "pedidos"
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    fecha = Column(DateTime, nullable=False, default=datetime.utcnow)
    estado = Column(Enum(EstadoPedido), nullable=False, default=EstadoPedido.pagado)
    metodo_pago = Column(Enum(MetodoPago), nullable=False)
    moneda = Column(String(3), nullable=False, default="ARS")
    descuento_tipo = Column(Enum(TipoDescuento), nullable=False, default=TipoDescuento.ningun)
    descuento_valor = Column(Float, nullable=False, default=0)
    subtotal = Column(Float, nullable=False, default=0)
    total = Column(Float, nullable=False, default=0)
    cliente = relationship("Cliente", back_populates="pedidos")
    detalles = relationship("DetallePedido", back_populates="pedido", cascade="all, delete-orphan")


class DetallePedido(Base):
    __tablename__ = "detalles_pedido"
    id = Column(Integer, primary_key=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Float, nullable=False)  # snapshot
    nombre_snapshot = Column(String(120), nullable=False)
    descuento_tipo = Column(Enum(TipoDescuento), nullable=False, default=TipoDescuento.ningun)
    descuento_valor = Column(Float, nullable=False, default=0)
    subtotal_linea = Column(Float, nullable=False)
    pedido = relationship("Pedido", back_populates="detalles")


class MovimientoStock(Base):
    __tablename__ = "movimientos_stock"
    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    tipo = Column(Enum(TipoMovimiento), nullable=False)
    cantidad = Column(Integer, nullable=False)
    stock_anterior = Column(Integer, nullable=False)
    stock_nuevo = Column(Integer, nullable=False)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=True)
    compra_id = Column(Integer, ForeignKey("compras.id", ondelete="SET NULL"), nullable=True)
    fecha = Column(DateTime, nullable=False, default=datetime.utcnow)
    producto = relationship("Producto", back_populates="movimientos")


class Proveedor(Base):
    __tablename__ = "proveedores"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(120), nullable=False, unique=True)
    contacto = Column(String(120), nullable=True)
    telefono = Column(String(40), nullable=True)
    alias = Column(String(120), nullable=True)
    dias_entrega = Column(String(120), nullable=True)
    movimientos = relationship("MovimientoProveedor", back_populates="proveedor", cascade="all, delete-orphan")


class MovimientoProveedor(Base):
    """Cuenta corriente por distribuidor: boleta 001 suma deuda, pagos 002/003 y N.crédito 004 restan."""
    __tablename__ = "movimientos_proveedor"
    id = Column(Integer, primary_key=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha = Column(DateTime, nullable=False, default=datetime.utcnow)
    tipo = Column(Enum(TipoMovProveedor), nullable=False)
    nro = Column(String(60), nullable=False)  # nro boleta; en pagos "PAGO <nro>" o el nro que referencia
    monto = Column(Float, nullable=False)
    proveedor = relationship("Proveedor", back_populates="movimientos")


class MovimientoCaja(Base):
    """Caja diaria: ENTRADA (ventas auto + extras manuales) y SALIDA (pagos a proveedor auto + gastos manuales)."""
    __tablename__ = "movimientos_caja"
    id = Column(Integer, primary_key=True)
    fecha = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    tipo = Column(Enum(TipoMovCaja), nullable=False)
    medio = Column(Enum(MetodoPago), nullable=False)  # EF/MP/DB/CD/TR (+ tarjeta legacy)
    descripcion = Column(String(250), nullable=False)
    monto = Column(Float, nullable=False)
    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="SET NULL"), nullable=True)
    compra_id = Column(Integer, ForeignKey("compras.id", ondelete="SET NULL"), nullable=True)


class Compra(Base):
    """Pedido a distribuidora: se registra, al entregarse entra stock, al pagarse sale caja."""
    __tablename__ = "compras"
    id = Column(Integer, primary_key=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False, index=True)
    fecha_pedido = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    nro_boleta = Column(String(60), nullable=False)
    fecha_entrega = Column(DateTime, nullable=True)  # null = "sin entregar"
    pagado = Column(Boolean, nullable=False, default=False)
    medio_pago = Column(Enum(MetodoPago), nullable=True)
    monto = Column(Float, nullable=False, default=0)  # calculado de las líneas
    proveedor = relationship("Proveedor")
    detalles = relationship("DetalleCompra", back_populates="compra", cascade="all, delete-orphan")


class DetalleCompra(Base):
    __tablename__ = "detalles_compra"
    id = Column(Integer, primary_key=True)
    compra_id = Column(Integer, ForeignKey("compras.id", ondelete="CASCADE"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    costo_unitario = Column(Float, nullable=False)  # snapshot (default: precio_costo)
    subtotal = Column(Float, nullable=False)
    compra = relationship("Compra", back_populates="detalles")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(60), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    rol = Column(String(20), nullable=False, default="vendedor")  # admin | vendedor
    activo = Column(Boolean, nullable=False, default=True)
