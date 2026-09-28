"""Tests for stock/inventory endpoints."""
import pytest
from httpx import AsyncClient


class TestStockIngreso:
    """Tests for POST /productos/{pid}/stock/ingreso."""

    async def test_ingreso_stock_increments(self, client: AsyncClient, admin_headers, session):
        """Stock ingreso increments stock and creates INGRESO movement."""
        from tests.factories import create_categoria, create_proveedor, create_producto
        from tests.assertions import assert_stock_movement, assert_producto_stock
        cat = create_categoria(session, nombre="CatIngreso")
        prov = create_proveedor(session, nombre="ProvIngreso")
        prod = create_producto(session, nombre="IngresoProd", precio_venta=100, stock=5, categorias=[cat], proveedor=prov)
        session.commit()

        resp = await client.post(
            f"/productos/{prod.id}/stock/ingreso",
            json={"cantidad": 10},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["producto_id"] == prod.id
        assert data["tipo"] == "INGRESO"
        assert data["cantidad"] == 10
        assert data["stock_anterior"] == 5
        assert data["stock_nuevo"] == 15

        assert_stock_movement(session, prod.id, "INGRESO", 10, 5, 15)
        assert_producto_stock(session, prod.id, 15)

    async def test_ingreso_stock_404(self, client: AsyncClient, admin_headers):
        """Stock ingreso for non-existent product returns 404."""
        resp = await client.post(
            "/productos/99999/stock/ingreso",
            json={"cantidad": 10},
            headers=admin_headers,
        )
        assert resp.status_code == 404

    async def test_ingreso_stock_cantidad_limits(self, client: AsyncClient, admin_headers, session):
        """Stock ingreso validates cantidad limits (gt=0, le=100000)."""
        from tests.factories import create_categoria, create_proveedor, create_producto
        cat = create_categoria(session, nombre="CatLimits")
        prov = create_proveedor(session, nombre="ProvLimits")
        prod = create_producto(session, precio_venta=100, stock=5, categorias=[cat], proveedor=prov)
        session.commit()

        resp = await client.post(
            f"/productos/{prod.id}/stock/ingreso",
            json={"cantidad": 0},
            headers=admin_headers,
        )
        assert resp.status_code == 422

        resp = await client.post(
            f"/productos/{prod.id}/stock/ingreso",
            json={"cantidad": 100001},
            headers=admin_headers,
        )
        assert resp.status_code == 422


class TestStockMovimientos:
    """Tests for GET /stock/movimientos."""

    async def test_movimientos_empty(self, client: AsyncClient, admin_headers):
        """Query movements returns empty list."""
        resp = await client.get("/stock/movimientos", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_movimientos_filter_producto_id(self, client: AsyncClient, admin_headers, session):
        """Filter movements by producto_id."""
        from tests.factories import create_categoria, create_proveedor, create_producto, create_movimiento_stock
        from app import models
        cat = create_categoria(session, nombre="CatMovFilter")
        prov = create_proveedor(session, nombre="ProvMovFilter")
        prod1 = create_producto(session, precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        prod2 = create_producto(session, precio_venta=200, stock=5, categorias=[cat], proveedor=prov)
        create_movimiento_stock(session, prod1, models.TipoMovimiento.INGRESO, 5)
        create_movimiento_stock(session, prod2, models.TipoMovimiento.INGRESO, 3)
        session.commit()

        resp = await client.get(f"/stock/movimientos?producto_id={prod1.id}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["producto_id"] == prod1.id

    async def test_movimientos_filter_fecha(self, client: AsyncClient, admin_headers, session):
        """Filter movements by fecha (single day)."""
        from tests.factories import create_categoria, create_proveedor, create_producto
        from app import models
        from datetime import datetime, timedelta
        cat = create_categoria(session, nombre="CatMovFecha")
        prov = create_proveedor(session, nombre="ProvMovFecha")
        prod = create_producto(session, precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        yesterday = datetime.utcnow() - timedelta(days=1)
        mov1 = models.MovimientoStock(
            producto_id=prod.id, tipo=models.TipoMovimiento.INGRESO, cantidad=5,
            stock_anterior=10, stock_nuevo=15, fecha=yesterday
        )
        mov2 = models.MovimientoStock(
            producto_id=prod.id, tipo=models.TipoMovimiento.INGRESO, cantidad=3,
            stock_anterior=15, stock_nuevo=18, fecha=datetime.utcnow()
        )
        session.add_all([mov1, mov2])
        session.commit()

        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        resp = await client.get(f"/stock/movimientos?fecha={today_str}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

    async def test_movimientos_filter_desde_hasta(self, client: AsyncClient, admin_headers, session):
        """Filter movements by desde and hasta date range."""
        from tests.factories import create_categoria, create_proveedor, create_producto
        from app import models
        from datetime import datetime, timedelta
        cat = create_categoria(session, nombre="CatMovRange")
        prov = create_proveedor(session, nombre="ProvMovRange")
        prod = create_producto(session, precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        three_days_ago = datetime.utcnow() - timedelta(days=3)
        two_days_ago = datetime.utcnow() - timedelta(days=2)
        mov1 = models.MovimientoStock(
            producto_id=prod.id, tipo=models.TipoMovimiento.INGRESO, cantidad=5,
            stock_anterior=10, stock_nuevo=15, fecha=three_days_ago
        )
        mov2 = models.MovimientoStock(
            producto_id=prod.id, tipo=models.TipoMovimiento.INGRESO, cantidad=3,
            stock_anterior=15, stock_nuevo=18, fecha=two_days_ago
        )
        mov3 = models.MovimientoStock(
            producto_id=prod.id, tipo=models.TipoMovimiento.INGRESO, cantidad=2,
            stock_anterior=18, stock_nuevo=20, fecha=datetime.utcnow()
        )
        session.add_all([mov1, mov2, mov3])
        session.commit()

        desde = (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%d")
        hasta = datetime.utcnow().strftime("%Y-%m-%d")
        resp = await client.get(f"/stock/movimientos?desde={desde}&hasta={hasta}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    async def test_movimientos_limit_500(self, client: AsyncClient, admin_headers, session):
        """Movements query limits to 500 results."""
        from tests.factories import create_categoria, create_proveedor, create_producto
        from app import models
        cat = create_categoria(session, nombre="CatLimit")
        prov = create_proveedor(session, nombre="ProvLimit")
        prod = create_producto(session, precio_venta=100, stock=1000, categorias=[cat], proveedor=prov)
        for i in range(600):
            ant = 10 + i
            mov = models.MovimientoStock(
                producto_id=prod.id, tipo=models.TipoMovimiento.INGRESO, cantidad=1,
                stock_anterior=ant, stock_nuevo=ant + 1
            )
            session.add(mov)
        session.commit()

        resp = await client.get("/stock/movimientos", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 500


class TestProveedoresCRUD:
    """Tests for proveedores CRUD."""

    async def test_create_proveedor(self, client: AsyncClient, admin_headers):
        """Create proveedor."""
        resp = await client.post(
            "/proveedores",
            json={"nombre": "Proveedor Test", "alias": "PT", "contacto": "Juan", "telefono": "123", "dias_entrega": "Lunes"},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] > 0
        assert data["nombre"] == "Proveedor Test"
        assert data["alias"] == "PT"

    async def test_create_proveedor_unique_nombre(self, client: AsyncClient, admin_headers):
        """Create duplicate proveedor returns 400."""
        await client.post("/proveedores", json={"nombre": "DupProv"}, headers=admin_headers)
        resp = await client.post("/proveedores", json={"nombre": "DupProv"}, headers=admin_headers)
        assert resp.status_code == 400

    async def test_list_proveedores(self, client: AsyncClient, admin_headers, session):
        """List proveedores."""
        from tests.factories import create_proveedor
        create_proveedor(session, nombre="ProvA", alias="A")
        create_proveedor(session, nombre="ProvB", alias="B")
        session.commit()

        resp = await client.get("/proveedores", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2


class TestProveedoresSaldos:
    """Tests for GET /proveedores/saldos."""

    async def test_saldos_calculates_debt(self, client: AsyncClient, admin_headers, session):
        """Saldos endpoint calculates debt per provider."""
        from tests.factories import create_proveedor, create_movimiento_proveedor
        from app import models
        prov1 = create_proveedor(session, nombre="ProvDeuda1", alias="PD1")
        prov2 = create_proveedor(session, nombre="ProvDeuda2", alias="PD2")
        create_movimiento_proveedor(session, prov1, models.TipoMovProveedor.BOLETA_001, "BOL-001", 1000)
        create_movimiento_proveedor(session, prov1, models.TipoMovProveedor.PAGO_EFECTIVO_002, "PAGO-001", 300)
        create_movimiento_proveedor(session, prov2, models.TipoMovProveedor.BOLETA_001, "BOL-002", 500)
        session.commit()

        resp = await client.get("/proveedores/saldos", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        p1 = next(p for p in data if p["nombre"] == "ProvDeuda1")
        p2 = next(p for p in data if p["nombre"] == "ProvDeuda2")
        assert p1["saldo"] == 700  # 1000 - 300
        assert p2["saldo"] == 500


class TestProveedoresMovimientos:
    """Tests for GET/POST /proveedores/{pid}/movimientos."""

    async def test_movimientos_chronological_with_saldo(self, client: AsyncClient, admin_headers, session):
        """Movimientos returns chronological list with running saldo."""
        from tests.factories import create_proveedor, create_movimiento_proveedor
        from app import models
        prov = create_proveedor(session, nombre="ProvMov", alias="PM")
        create_movimiento_proveedor(session, prov, models.TipoMovProveedor.BOLETA_001, "BOL-001", 1000)
        create_movimiento_proveedor(session, prov, models.TipoMovProveedor.PAGO_EFECTIVO_002, "PAGO-001", 300)
        create_movimiento_proveedor(session, prov, models.TipoMovProveedor.NOTA_CREDITO_004, "NC-001", 100)
        session.commit()

        resp = await client.get(f"/proveedores/{prov.id}/movimientos", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert data[0]["saldo"] == 1000
        assert data[1]["saldo"] == 700
        assert data[2]["saldo"] == 600

    async def test_create_movimiento_001_increases_debt(self, client: AsyncClient, admin_headers, session):
        """Create BOLETA_001 increases debt."""
        from tests.factories import create_proveedor
        prov = create_proveedor(session, nombre="Prov001")
        session.commit()

        resp = await client.post(
            f"/proveedores/{prov.id}/movimientos",
            json={"tipo": "BOLETA_001", "nro": "BOL-001", "monto": 1000},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["tipo"] == "BOLETA_001"
        assert data["saldo"] == 1000

    async def test_create_movimiento_002_003_decreases_debt_creates_caja(self, client: AsyncClient, admin_headers, session):
        """Create PAGO_EFECTIVO_002/PAGO_TRANSFER_003 decreases debt and creates caja SALIDA."""
        from tests.factories import create_proveedor, create_movimiento_proveedor
        from tests.assertions import assert_caja_movement
        from app import models
        prov = create_proveedor(session, nombre="ProvPago")
        create_movimiento_proveedor(session, prov, models.TipoMovProveedor.BOLETA_001, "BOL-001", 1000)
        session.commit()

        resp = await client.post(
            f"/proveedores/{prov.id}/movimientos",
            json={"tipo": "PAGO_EFECTIVO_002", "nro": "PAGO-001", "monto": 300},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["saldo"] == 700

        assert_caja_movement(session, "SALIDA", "efectivo", f"Pago {prov.nombre}", 300)

    async def test_create_movimiento_004_decreases_debt(self, client: AsyncClient, admin_headers, session):
        """Create NOTA_CREDITO_004 decreases debt."""
        from tests.factories import create_proveedor, create_movimiento_proveedor
        from app import models
        prov = create_proveedor(session, nombre="ProvNC")
        create_movimiento_proveedor(session, prov, models.TipoMovProveedor.BOLETA_001, "BOL-001", 1000)
        session.commit()

        resp = await client.post(
            f"/proveedores/{prov.id}/movimientos",
            json={"tipo": "NOTA_CREDITO_004", "nro": "NC-001", "monto": 100},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["saldo"] == 900


class TestReportesVentas:
    """Tests for GET /reportes/ventas."""

    async def test_ventas_count_and_total(self, client: AsyncClient, admin_headers, session):
        """Ventas report returns count and total for pagado orders."""
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto, create_pedido
        from app import models
        cat = create_categoria(session, nombre="CatRep")
        prov = create_proveedor(session, nombre="ProvRep")
        prod = create_producto(session, precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        cli = create_cliente(session, nombre="CliRep", email="rep@test.com", dni="16161616")
        create_pedido(session, cli, [{"producto": prod, "cantidad": 2}], estado=models.EstadoPedido.pagado)
        create_pedido(session, cli, [{"producto": prod, "cantidad": 1}], estado=models.EstadoPedido.cancelado)
        session.commit()

        resp = await client.get("/reportes/ventas", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["cantidad_pedidos"] == 1
        assert data["total_ars"] == 200.0

    async def test_ventas_filter_fecha(self, client: AsyncClient, admin_headers, session):
        """Ventas report filters by fecha."""
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto, create_pedido
        from app import models
        from datetime import datetime, timedelta
        cat = create_categoria(session, nombre="CatRepFecha")
        prov = create_proveedor(session, nombre="ProvRepFecha")
        prod = create_producto(session, precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        cli = create_cliente(session, nombre="CliRepFecha", email="repf@test.com", dni="17171717")
        yesterday = datetime.utcnow() - timedelta(days=1)
        create_pedido(session, cli, [{"producto": prod, "cantidad": 1}], fecha=yesterday, estado=models.EstadoPedido.pagado)
        create_pedido(session, cli, [{"producto": prod, "cantidad": 1}], estado=models.EstadoPedido.pagado)
        session.commit()

        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        resp = await client.get(f"/reportes/ventas?fecha={today_str}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["cantidad_pedidos"] == 1

    async def test_ventas_filter_desde_hasta(self, client: AsyncClient, admin_headers, session):
        """Ventas report filters by desde and hasta."""
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto, create_pedido
        from app import models
        from datetime import datetime, timedelta
        cat = create_categoria(session, nombre="CatRepRange")
        prov = create_proveedor(session, nombre="ProvRepRange")
        prod = create_producto(session, precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        cli = create_cliente(session, nombre="CliRepRange", email="repr@test.com", dni="18181818")
        three_days_ago = datetime.utcnow() - timedelta(days=3)
        two_days_ago = datetime.utcnow() - timedelta(days=2)
        create_pedido(session, cli, [{"producto": prod, "cantidad": 1}], fecha=three_days_ago, estado=models.EstadoPedido.pagado)
        create_pedido(session, cli, [{"producto": prod, "cantidad": 1}], fecha=two_days_ago, estado=models.EstadoPedido.pagado)
        create_pedido(session, cli, [{"producto": prod, "cantidad": 1}], estado=models.EstadoPedido.pagado)
        session.commit()

        desde = (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%d")
        hasta = datetime.utcnow().strftime("%Y-%m-%d")
        resp = await client.get(f"/reportes/ventas?desde={desde}&hasta={hasta}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["cantidad_pedidos"] == 2