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
    tarjeta = "tarjeta"
    transferencia = "transferencia"
    mercadopago = "mercadopago"


class TipoDescuento(str, enum.Enum):
    ningun = "ningun"
    porcentaje = "porcentaje"
    monto_fijo = "monto_fijo"


class TipoMovimiento(str, enum.Enum):
    INGRESO = "INGRESO"
    EGRESO_VENTA = "EGRESO_VENTA"
    AJUSTE = "AJUSTE"
    DEVOLUCION_CANCEL = "DEVOLUCION_CANCEL"


producto_categoria = Table(
    "producto_categoria",
    Base.metadata,
    Column("producto_id", ForeignKey("productos.id", ondelete="CASCADE"), primary_key=True),
    Column("categoria_id", ForeignKey("categorias.id", ondelete="CASCADE"), primary_key=True),
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
    categorias = relationship("Categoria", secondary=producto_categoria, back_populates="productos")
    movimientos = relationship("MovimientoStock", back_populates="producto")


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
    fecha = Column(DateTime, nullable=False, default=datetime.utcnow)
    producto = relationship("Producto", back_populates="movimientos")


class Proveedor(Base):
    __tablename__ = "proveedores"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(120), nullable=False, unique=True)
    contacto = Column(String(120), nullable=True)
    telefono = Column(String(40), nullable=True)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(60), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    rol = Column(String(20), nullable=False, default="vendedor")  # admin | vendedor
    activo = Column(Boolean, nullable=False, default=True)
