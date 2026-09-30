"""Utilidades para cálculos monetarios exactos."""
from decimal import Decimal

CENT = Decimal("0.01")


def money(value) -> Decimal:
    """Convierte un valor numérico a Decimal con precisión de centavos."""
    return Decimal(str(value if value is not None else 0)).quantize(CENT)
