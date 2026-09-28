"""Tests for pure business logic services."""
import pytest


class TestAplicarDescuento:
    """Tests for aplicar_descuento service function."""

    def test_ningun_returns_base(self):
        """No discount returns base."""
        from app.services.discounts import aplicar_descuento
        from app.models import TipoDescuento

        assert aplicar_descuento(1000.0, TipoDescuento.ningun.value, 0) == 1000.0
        assert aplicar_descuento(1000.0, TipoDescuento.ningun.value, 10) == 1000.0
        assert aplicar_descuento(999.99, "ningun", 0) == 999.99

    def test_zero_valor_returns_base(self):
        """Zero discount value returns base regardless of type."""
        from app.services.discounts import aplicar_descuento
        from app.models import TipoDescuento

        assert aplicar_descuento(1000.0, TipoDescuento.porcentaje.value, 0) == 1000.0
        assert aplicar_descuento(1000.0, TipoDescuento.monto_fijo.value, 0) == 1000.0

    def test_porcentaje_calculates_correctly(self):
        """Percentage discount calculates correctly."""
        from app.services.discounts import aplicar_descuento
        from app.models import TipoDescuento

        assert aplicar_descuento(1000.0, TipoDescuento.porcentaje.value, 10) == 900.0
        assert aplicar_descuento(1000.0, TipoDescuento.porcentaje.value, 25) == 750.0
        assert aplicar_descuento(100.0, TipoDescuento.porcentaje.value, 50) == 50.0
        assert aplicar_descuento(100.0, "porcentaje", 100) == 0.0

    def test_porcentaje_rejects_invalid(self):
        """Percentage discount rejects values outside 0-100."""
        from app.services.discounts import aplicar_descuento
        from app.models import TipoDescuento

        with pytest.raises(ValueError, match="porcentaje debe estar entre 0 y 100"):
            aplicar_descuento(1000.0, TipoDescuento.porcentaje.value, -1)
        with pytest.raises(ValueError, match="porcentaje debe estar entre 0 y 100"):
            aplicar_descuento(1000.0, TipoDescuento.porcentaje.value, 101)

    def test_monto_fijo_calculates_correctly(self):
        """Fixed amount discount calculates correctly."""
        from app.services.discounts import aplicar_descuento
        from app.models import TipoDescuento

        assert aplicar_descuento(1000.0, TipoDescuento.monto_fijo.value, 150) == 850.0
        assert aplicar_descuento(100.0, TipoDescuento.monto_fijo.value, 30) == 70.0
        assert aplicar_descuento(1000.0, "monto_fijo", 1000) == 0.0

    def test_monto_fijo_rejects_invalid(self):
        """Fixed amount discount rejects values < 0 or > base."""
        from app.services.discounts import aplicar_descuento
        from app.models import TipoDescuento

        with pytest.raises(ValueError, match="monto_fijo no puede superar la base"):
            aplicar_descuento(1000.0, TipoDescuento.monto_fijo.value, -1)
        with pytest.raises(ValueError, match="monto_fijo no puede superar la base"):
            aplicar_descuento(1000.0, TipoDescuento.monto_fijo.value, 1200)

    def test_unknown_tipo_raises(self):
        """Unknown discount type raises ValueError."""
        from app.services.discounts import aplicar_descuento

        with pytest.raises(ValueError, match="tipo descuento desconocido"):
            aplicar_descuento(1000.0, "inventado", 10)