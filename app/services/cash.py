"""Operaciones de caja.

Los movimientos generados por ventas/compras se crean aquí para mantener
un único punto de escritura de caja. No se hace commit en helpers internos.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app import models, schemas
from app.services.money import money
from app.core.time import local_datetime_to_utc_naive, utc_now


class CashError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def registrar(
    db: Session,
    *,
    tipo: models.TipoMovCaja,
    medio: models.MetodoPago,
    descripcion: str,
    monto: float,
    fecha: datetime | None = None,
    pedido_id: int | None = None,
    compra_id: int | None = None,
):
    monto = money(monto)
    if monto <= 0:
        raise CashError(422, "El monto de caja debe ser mayor a 0")
    movimiento = models.MovimientoCaja(
        tipo=tipo,
        medio=medio,
        descripcion=descripcion.strip(),
        monto=monto,
        fecha=fecha or utc_now(),
        pedido_id=pedido_id,
        compra_id=compra_id,
    )
    db.add(movimiento)
    return movimiento


def crear_manual(db: Session, data: schemas.MovimientoCajaCreate):
    movimiento = registrar(
        db,
        tipo=data.tipo,
        medio=data.medio,
        descripcion=data.descripcion,
        monto=data.monto,
        fecha=local_datetime_to_utc_naive(data.fecha) if data.fecha else None,
    )
    db.commit()
    db.refresh(movimiento)
    return movimiento


def eliminar_manual(db: Session, movimiento_id: int) -> None:
    movimiento = db.get(models.MovimientoCaja, movimiento_id)
    if not movimiento:
        raise CashError(404, "Movimiento no encontrado")
    automatico = (
        movimiento.pedido_id is not None
        or movimiento.compra_id is not None
        or movimiento.descripcion.startswith("Pago ")
    )
    if automatico:
        raise CashError(
            400,
            "Movimiento automático: no se borra, se anula desde la operación origen",
        )
    db.delete(movimiento)
    db.commit()
