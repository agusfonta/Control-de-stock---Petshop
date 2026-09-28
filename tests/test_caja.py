"""Tests for caja endpoints."""
import pytest
from httpx import AsyncClient


class TestCajaResumen:
    """Tests for GET /caja."""

    async def test_resumen_empty(self, client: AsyncClient, admin_headers):
        """Resumen returns empty when no movements."""
        resp = await client.get("/caja", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["movimientos"] == []
        assert data["total_entrada"] == 0.0
        assert data["total_salida"] == 0.0
        assert data["balance"] == 0.0
        assert data["por_medio"] == {}

    async def test_resumen_calculates_totals(self, client: AsyncClient, admin_headers, session):
        """Resumen calculates totals, balance, and por_medio correctly."""
        from tests.factories import create_movimiento_caja
        from app import models

        create_movimiento_caja(session, models.TipoMovCaja.ENTRADA, models.MetodoPago.efectivo, "Venta #1", 1000.0)
        create_movimiento_caja(session, models.TipoMovCaja.ENTRADA, models.MetodoPago.transferencia, "Venta #2", 500.0)
        create_movimiento_caja(session, models.TipoMovCaja.SALIDA, models.MetodoPago.efectivo, "Gasto", 200.0)
        create_movimiento_caja(session, models.TipoMovCaja.SALIDA, models.MetodoPago.efectivo, "Pago Proveedor", 300.0)
        session.commit()

        resp = await client.get("/caja", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["movimientos"]) == 4
        assert data["total_entrada"] == 1500.0
        assert data["total_salida"] == 500.0
        assert data["balance"] == 1000.0
        assert data["por_medio"]["efectivo"]["entrada"] == 1000.0
        assert data["por_medio"]["efectivo"]["salida"] == 500.0
        assert data["por_medio"]["transferencia"]["entrada"] == 500.0
        assert data["por_medio"]["transferencia"]["salida"] == 0.0

    async def test_resumen_filters_by_fecha(self, client: AsyncClient, admin_headers, session):
        """Resumen filters by fecha (single day)."""
        from tests.factories import create_movimiento_caja
        from app import models
        from datetime import datetime, timedelta

        yesterday = datetime.utcnow() - timedelta(days=1)
        # Create movement with specific date by adding directly
        mov1 = models.MovimientoCaja(
            tipo=models.TipoMovCaja.ENTRADA,
            medio=models.MetodoPago.efectivo,
            descripcion="Ayer",
            monto=1000.0,
            fecha=yesterday,
        )
        session.add(mov1)
        create_movimiento_caja(session, models.TipoMovCaja.ENTRADA, models.MetodoPago.efectivo, "Hoy", 500.0)
        session.commit()

        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        resp = await client.get(f"/caja?fecha={today_str}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_entrada"] == 500.0
        assert len(data["movimientos"]) == 1


class TestCajaCreate:
    """Tests for POST /caja."""

    async def test_create_manual_movement(self, client: AsyncClient, admin_headers, session):
        """Create manual caja movement succeeds."""
        resp = await client.post(
            "/caja",
            json={
                "tipo": "ENTRADA",
                "medio": "efectivo",
                "descripcion": "Apertura de caja",
                "monto": 5000.0,
                "fecha": "2026-01-15T08:00:00",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] > 0
        assert data["tipo"] == "ENTRADA"
        assert data["medio"] == "efectivo"
        assert data["descripcion"] == "Apertura de caja"
        assert data["monto"] == 5000.0
        assert data["automatico"] is False

    async def test_create_manual_movement_requires_auth(self, client: AsyncClient):
        """Create manual movement requires authentication."""
        resp = await client.post(
            "/caja",
            json={"tipo": "ENTRADA", "medio": "efectivo", "descripcion": "Test", "monto": 100},
        )
        assert resp.status_code == 401


class TestCajaDelete:
    """Tests for DELETE /caja/{id}."""

    async def test_delete_manual_movement_succeeds(self, client: AsyncClient, admin_headers, session):
        """Delete manual movement succeeds."""
        from tests.factories import create_movimiento_caja
        from app import models

        mov = create_movimiento_caja(session, models.TipoMovCaja.ENTRADA, models.MetodoPago.efectivo, "Manual test", 100.0)
        session.commit()

        resp = await client.delete(f"/caja/{mov.id}", headers=admin_headers)
        assert resp.status_code == 204

        deleted = session.get(models.MovimientoCaja, mov.id)
        assert deleted is None

    async def test_delete_automatic_movement_returns_400(self, client: AsyncClient, admin_headers, session):
        """Delete automatic movement (from sale/payment) returns 400."""
        from tests.factories import create_movimiento_caja
        from app import models

        # Simulate automatic movement (has pedido_id or starts with "Pago ")
        mov = models.MovimientoCaja(
            tipo=models.TipoMovCaja.ENTRADA,
            medio=models.MetodoPago.efectivo,
            descripcion="Venta #123 · Cliente Test",
            monto=200.0,
            pedido_id=123,
        )
        session.add(mov)
        session.commit()

        resp = await client.delete(f"/caja/{mov.id}", headers=admin_headers)
        assert resp.status_code == 400
        assert "automático" in resp.json()["detail"].lower()
        assert "anula desde" in resp.json()["detail"].lower()

    async def test_delete_automatic_pago_movement_returns_400(self, client: AsyncClient, admin_headers, session):
        """Delete automatic 'Pago ' movement returns 400."""
        from tests.factories import create_movimiento_caja
        from app import models

        mov = create_movimiento_caja(session, models.TipoMovCaja.SALIDA, models.MetodoPago.efectivo, "Pago Proveedor BOL-001", 300.0)
        session.commit()

        resp = await client.delete(f"/caja/{mov.id}", headers=admin_headers)
        assert resp.status_code == 400
        assert "automático" in resp.json()["detail"].lower()

    async def test_delete_non_existent_returns_404(self, client: AsyncClient, admin_headers):
        """Delete non-existent movement returns 404."""
        resp = await client.delete("/caja/99999", headers=admin_headers)
        assert resp.status_code == 404


class TestCajaVentaMixta:
    """Tests for caja resumen with multi-payment sales."""

    async def test_resumen_venta_mixta_por_medio(self, client: AsyncClient, admin_headers, session):
        """Resumen desglosa cada medio de una venta mixta."""
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto
        cat = create_categoria(session)
        prov = create_proveedor(session)
        prod = create_producto(session, precio_venta=1000, stock=10, categorias=[cat], proveedor=prov)
        cli = create_cliente(session)
        session.commit()

        resp = await client.post(
            "/pedidos",
            json={
                "cliente_id": cli.id,
                "metodo_pago": "efectivo",
                "detalles": [{"producto_id": prod.id, "cantidad": 1}],
                "pagos": [
                    {"metodo": "efectivo", "monto": 600},
                    {"metodo": "debito", "monto": 400},
                ],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201

        resumen = await client.get("/caja", headers=admin_headers)
        assert resumen.status_code == 200
        data = resumen.json()
        assert data["total_entrada"] == 1000.0
        assert data["por_medio"]["efectivo"]["entrada"] == 600.0
        assert data["por_medio"]["debito"]["entrada"] == 400.0