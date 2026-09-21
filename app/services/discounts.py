"""Cálculo de descuentos combinados."""
from app.models import TipoDescuento


def aplicar_descuento(base: float, tipo: TipoDescuento | str, valor: float) -> float:
    t = str(tipo)
    if t == "ningun" or valor == 0:
        return round(base, 2)
    if t == "porcentaje":
        if valor < 0 or valor > 100:
            raise ValueError("porcentaje debe estar entre 0 y 100")
        return round(base * (1 - valor / 100), 2)
    if t == "monto_fijo":
        if valor < 0 or valor > base:
            raise ValueError("monto_fijo no puede superar la base")
        return round(base - valor, 2)
    raise ValueError(f"tipo descuento desconocido: {tipo}")
