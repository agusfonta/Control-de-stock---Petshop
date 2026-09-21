"""Schemas Pydantic v2 con validación estricta."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator, model_validator

from app.models import MetodoPago, TipoDescuento, Unidad


def _url_ok_value(v):
    if v in (None, ""):
        return None
    s = str(v)
    if not (s.startswith("http://") or s.startswith("https://")):
        raise ValueError("imagen_url debe ser URL http(s)")
    return v


# ---------- Categorias ----------
class CategoriaCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    descripcion: Optional[str] = Field(default=None, max_length=500)


class CategoriaOut(CategoriaCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- Productos ----------
class ProductoCreate(BaseModel):
    sku: Optional[str] = Field(default=None, max_length=60)
    nombre: str = Field(min_length=2, max_length=120)
    descripcion: Optional[str] = None
    marca: Optional[str] = Field(default=None, max_length=80)
    unidad: Unidad = Unidad.unidad
    precio_costo: float = Field(ge=0)
    precio_venta: float = Field(gt=0)
    stock: int = Field(ge=0)
    stock_minimo: int = Field(default=10, ge=0)
    imagen_url: Optional[str] = None
    activo: bool = True
    # Un producto puede quedar "Sin categoría" (ej: se borró su categoría).
    # Desde el panel se le puede asignar otra después.
    categoria_ids: List[int] = Field(default_factory=list)

    @field_validator("imagen_url")
    @classmethod
    def _url_ok(cls, v):
        return _url_ok_value(v)


class ProductoUpdate(BaseModel):
    sku: Optional[str] = Field(default=None, max_length=60)
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=120)
    descripcion: Optional[str] = None
    marca: Optional[str] = Field(default=None, max_length=80)
    unidad: Optional[Unidad] = None
    precio_costo: Optional[float] = Field(default=None, ge=0)
    precio_venta: Optional[float] = Field(default=None, gt=0)
    stock: Optional[int] = Field(default=None, ge=0)
    stock_minimo: Optional[int] = Field(default=None, ge=0)
    imagen_url: Optional[str] = None
    activo: Optional[bool] = None
    categoria_ids: Optional[List[int]] = None

    @field_validator("imagen_url")
    @classmethod
    def _url_ok(cls, v):
        return _url_ok_value(v)


class ProductoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sku: Optional[str] = None
    nombre: str
    descripcion: Optional[str] = None
    marca: Optional[str] = None
    unidad: Unidad
    precio_costo: float
    precio_venta: float
    stock: int
    stock_minimo: int
    imagen_url: Optional[str] = None
    activo: bool
    categorias: List[CategoriaOut] = []
    stock_bajo: bool = False


# ---------- Clientes ----------
class ClienteCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    email: EmailStr
    telefono: Optional[str] = Field(default=None, max_length=40)
    dni: str = Field(min_length=7, max_length=20)
    direccion: Optional[str] = Field(default=None, max_length=250)


class ClienteOut(ClienteCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- Pedidos ----------
class DetalleIn(BaseModel):
    producto_id: int
    cantidad: int = Field(ge=1)
    descuento_tipo: TipoDescuento = TipoDescuento.ningun
    descuento_valor: float = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _desc_ok(self):
        if self.descuento_tipo == TipoDescuento.porcentaje and self.descuento_valor > 100:
            raise ValueError("descuento porcentaje linea max 100")
        if self.descuento_tipo == TipoDescuento.ningun and self.descuento_valor != 0:
            raise ValueError("si tipo es ningun, valor debe ser 0")
        return self


class PedidoCreate(BaseModel):
    cliente_id: int
    metodo_pago: MetodoPago
    descuento_tipo: TipoDescuento = TipoDescuento.ningun
    descuento_valor: float = Field(default=0, ge=0)
    detalles: List[DetalleIn] = Field(min_length=1)

    @model_validator(mode="after")
    def _desc_ok(self):
        if self.descuento_tipo == TipoDescuento.porcentaje and self.descuento_valor > 100:
            raise ValueError("descuento porcentaje pedido max 100")
        if self.descuento_tipo == TipoDescuento.ningun and self.descuento_valor != 0:
            raise ValueError("si tipo es ningun, valor debe ser 0")
        return self


class DetalleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    producto_id: int
    cantidad: int
    precio_unitario: float
    nombre_snapshot: str
    descuento_tipo: TipoDescuento
    descuento_valor: float
    subtotal_linea: float


class PedidoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cliente_id: int
    fecha: datetime
    estado: str
    metodo_pago: MetodoPago
    moneda: str
    descuento_tipo: TipoDescuento
    descuento_valor: float
    subtotal: float
    total: float
    detalles: List[DetalleOut] = []


# ---------- Stock / Proveedor / Auth ----------
class IngresoStockIn(BaseModel):
    cantidad: int = Field(gt=0, le=100000)


class MovimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    producto_id: int
    tipo: str
    cantidad: int
    stock_anterior: int
    stock_nuevo: int
    pedido_id: Optional[int] = None
    fecha: datetime


class ProveedorCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    contacto: Optional[str] = Field(default=None, max_length=120)
    telefono: Optional[str] = Field(default=None, max_length=40)


class ProveedorOut(ProveedorCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=60)
    password: str = Field(min_length=6, max_length=100)
    rol: str = Field(default="vendedor")

    @field_validator("rol")
    @classmethod
    def _rol(cls, v):
        if v not in ("admin", "vendedor"):
            raise ValueError("rol debe ser admin o vendedor")
        return v


class LoginIn(BaseModel):
    username: str
    password: str
