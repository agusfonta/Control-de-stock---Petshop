"""Casos de uso de compras a proveedores."""

from sqlalchemy.orm import Session
from datetime import timedelta

from app import models, schemas
from app.services import stock as stock_service
from app.services import cash as cash_service
from app.services.money import money
from app.core.time import local_datetime_to_utc_naive, utc_now


class PurchaseError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _armar_detalles(
    db: Session, detalles_in: list[schemas.DetalleCompraIn]
):
    detalles = []
    monto = money(0)
    for item in detalles_in:
        producto = db.get(models.Producto, item.producto_id)
        if not producto:
            raise PurchaseError(404, f"Producto {item.producto_id} no existe")
        costo = (
            item.costo_unitario
            if item.costo_unitario is not None
            else (producto.precio_costo or 0)
        )
        costo = money(costo)
        subtotal = money(costo * item.cantidad)
        monto = money(monto + subtotal)
        detalles.append(
            models.DetalleCompra(
                producto_id=producto.id,
                cantidad=item.cantidad,
                costo_unitario=costo,
                subtotal=subtotal,
            )
        )
    if not detalles:
        raise PurchaseError(422, "La compra necesita al menos una línea")
    return detalles, monto


def crear_compra(db: Session, data: schemas.CompraCreate) -> models.Compra:
    proveedor = db.get(models.Proveedor, data.proveedor_id)
    if not proveedor:
        raise PurchaseError(404, "Distribuidora no existe")

    detalles, monto = _armar_detalles(db, data.detalles)
    compra = models.Compra(
        proveedor_id=proveedor.id,
        nro_boleta=data.nro_boleta.strip(),
        fecha_pedido=local_datetime_to_utc_naive(data.fecha_pedido) if data.fecha_pedido else utc_now(),
        pagado=data.pagado,
        medio_pago=data.medio_pago,
        monto=monto,
        detalles=detalles,
    )
    db.add(compra)
    db.flush()

    if data.pagado:
        cash_service.registrar(
            db,
            tipo=models.TipoMovCaja.SALIDA,
            medio=data.medio_pago,
            descripcion=f"Pago {proveedor.nombre} {compra.nro_boleta}",
            monto=monto,
            fecha=compra.fecha_pedido,
            compra_id=compra.id,
        )

    db.commit()
    return compra


def actualizar_compra(
    db: Session, compra_id: int, data: schemas.CompraUpdate
) -> models.Compra:
    compra = db.get(models.Compra, compra_id)
    if not compra:
        raise PurchaseError(404, "Compra no encontrada")
    if data.nro_boleta is not None:
        compra.nro_boleta = data.nro_boleta.strip()
    if data.fecha_pedido is not None:
        compra.fecha_pedido = local_datetime_to_utc_naive(data.fecha_pedido)
    if data.medio_pago is not None:
        compra.medio_pago = data.medio_pago
    if data.detalles is not None:
        if compra.fecha_entrega is not None:
            raise PurchaseError(400, "Ya entregada: las líneas no se pueden editar")
        if compra.pagos:
            raise PurchaseError(400, "Con pagos registrados no se pueden cambiar las líneas")
        for old in list(compra.detalles):
            db.delete(old)
        db.flush()
        compra.detalles, compra.monto = _armar_detalles(db, data.detalles)
    db.commit()
    return compra


def entregar_compra(db: Session, compra_id: int) -> models.Compra:
    compra = db.get(models.Compra, compra_id)
    if not compra:
        raise PurchaseError(404, "Compra no encontrada")
    if compra.fecha_entrega is not None:
        raise PurchaseError(400, "Ya estaba entregada")

    ahora = utc_now()
    for detalle in compra.detalles:
        producto = db.get(models.Producto, detalle.producto_id)
        if not producto:
            raise PurchaseError(
                404, f"Producto {detalle.producto_id} de la compra no existe"
            )
        try:
            stock_service.ingresar(
                db,
                producto,
                detalle.cantidad,
                compra_id=compra.id,
                fecha=ahora,
            )
        except stock_service.StockError as e:
            raise PurchaseError(422, str(e))

    compra.fecha_entrega = ahora
    db.commit()
    return compra


def _saldo_pendiente(compra: models.Compra) -> object:
    total_aplicado = money(sum((p.monto + p.descuento for p in (compra.pagos or [])), money(0)))
    if compra.pagado and not compra.pagos:
        return money(0)
    return money(max(money(0), compra.monto - total_aplicado))


def sugerir_descuento_pronto_pago(compra: models.Compra) -> object:
    proveedor = compra.proveedor
    dias = getattr(proveedor, "pronto_pago_dias", None)
    porcentaje = getattr(proveedor, "pronto_pago_porcentaje", None)
    if dias is None or porcentaje is None or porcentaje <= 0:
        return money(0)
    hoy = utc_now()
    if hoy.date() > (compra.fecha_pedido.date() + timedelta(days=dias)):
        return money(0)
    saldo = _saldo_pendiente(compra)
    return money(saldo * money(porcentaje) / money(100))


def pagar_compra(db: Session, compra_id: int, data: dict) -> models.Compra:
    compra = db.get(models.Compra, compra_id)
    if not compra:
        raise PurchaseError(404, "Compra no encontrada")

    saldo = _saldo_pendiente(compra)
    if compra.pagado and not compra.pagos:
        raise PurchaseError(400, "Ya estaba pagada")
    if saldo <= 0:
        raise PurchaseError(400, "La compra ya está saldada")

    medio = (data or {}).get("medio_pago") or (
        compra.medio_pago.value if compra.medio_pago else None
    )
    if not medio:
        raise PurchaseError(422, "Indicar medio_pago para registrar el pago")
    try:
        medio_enum = models.MetodoPago(medio)
    except ValueError:
        raise PurchaseError(422, f"medio_pago inválido: {medio}")

    raw_monto = (data or {}).get("monto")
    monto = money(saldo if raw_monto is None else raw_monto)
    descuento = money((data or {}).get("descuento", 0))
    aplicado = money(monto + descuento)
    if aplicado <= 0:
        raise PurchaseError(422, "El pago o descuento debe ser mayor a 0")
    if aplicado > saldo + money("0.01"):
        raise PurchaseError(422, f"El pago supera el saldo pendiente ${saldo:.2f}")

    pago = models.PagoCompra(
        compra_id=compra.id,
        fecha=utc_now(),
        medio=medio_enum,
        monto=monto,
        descuento=descuento,
    )
    db.add(pago)
    db.flush()

    compra.medio_pago = medio_enum
    nuevo_saldo = money(saldo - aplicado)
    compra.pagado = nuevo_saldo <= money("0.01")

    if monto > 0:
        cash_service.registrar(
            db,
            tipo=models.TipoMovCaja.SALIDA,
            medio=medio_enum,
            descripcion=f"Pago {compra.proveedor.nombre} {compra.nro_boleta}",
            monto=monto,
            compra_id=compra.id,
        )
    db.commit()
    return compra

def eliminar_compra(db: Session, compra_id: int) -> None:
    compra = db.get(models.Compra, compra_id)
    if not compra:
        raise PurchaseError(404, "Compra no encontrada")
    if compra.fecha_entrega is not None:
        raise PurchaseError(400, "Ya entregada: no se puede borrar")
    if compra.pagado:
        raise PurchaseError(400, "Ya pagada: no se puede borrar")
    if compra.pagos:
        raise PurchaseError(400, "Con pagos registrados no se puede borrar")
    db.query(models.MovimientoCaja).filter(
        models.MovimientoCaja.compra_id == compra_id
    ).delete()
    db.delete(compra)
    db.commit()
