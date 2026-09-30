"""Cálculo de descuentos monetarios exactos."""
from decimal import Decimal

from app.models import TipoDescuento
from app.services.money import money


def aplicar_descuento(base, tipo: TipoDescuento | str, valor) -> Decimal:
    base = money(base)
    valor = money(valor)
    t = tipo.value if isinstance(tipo, TipoDescuento) else str(tipo)
    if t == "ningun" or valor == 0:
        return base
    if t == "porcentaje":
        if valor < 0 or valor > 100:
            raise ValueError("porcentaje debe estar entre 0 y 100")
        return money(base * (Decimal("1") - valor / Decimal("100")))
    if t == "monto_fijo":
        if valor < 0 or valor > base:
            raise ValueError("monto_fijo no puede superar la base")
        return money(base - valor)
    raise ValueError(f"tipo descuento desconocido: {tipo}")
