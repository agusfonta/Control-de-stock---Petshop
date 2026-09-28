"""Tests for compras endpoints."""
import pytest
from httpx import AsyncClient


class TestComprasCreate:
    """Tests for POST /compras."""

    async def test_create_compra_valid(self, client: AsyncClient, admin_headers, session):
        """Create purchase with valid data."""
        from tests.factories import create_proveedor, create_categoria, create_producto
        prov = create_proveedor(session, nombre="ProvCompra", alias="PC")
        cat = create_categoria(session, nombre="CatCompra")
        prod = create_producto(session, nombre="ProdCompra", precio_venta=100, precio_costo=60, stock=10, categorias=[cat], proveedor=prov)
        session.commit()

        resp = await client.post(
            "/compras",
            json={
                "proveedor_id": prov.id,
                "nro_boleta": "BOL-001",
                "fecha_pedido": "2026-01-15T10:00:00",
                "detalles": [{"producto_id": prod.id, "cantidad": 5}],
                "pagado": False,
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] > 0
        assert data["proveedor_id"] == prov.id
        assert data["nro_boleta"] == "BOL-001"
        assert data["monto"] == 300.0
        assert len(data["detalles"]) == 1
        assert data["detalles"][0]["cantidad"] == 5

    async def test_create_compra_proveedor_exists(self, client: AsyncClient, admin_headers):
        """Create purchase with non-existent proveedor returns 404/422."""
        resp = await client.post(
            "/compras",
            json={
                "proveedor_id": 99999,
                "nro_boleta": "BOL-TEST",
                "detalles": [{"producto_id": 1, "cantidad": 1}],
            },
            headers=admin_headers,
        )
        assert resp.status_code in (404, 422)
        detail = resp.json()
        if isinstance(detail, dict):
            detail = detail.get("detail", "")
        if isinstance(detail, list):
            detail = str(detail)
        assert "distribuidora no existe" in detail.lower()

    async def test_create_compra_at_least_one_line(self, client: AsyncClient, admin_headers, session):
        """Create purchase with empty detalles returns 422."""
        from tests.factories import create_proveedor
        prov = create_proveedor(session, nombre="ProvEmpty")
        session.commit()

        resp = await client.post(
            "/compras",
            json={
                "proveedor_id": prov.id,
                "nro_boleta": "BOL-EMPTY",
                "detalles": [],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 422
        detail = resp.json()
        if isinstance(detail, dict):
            detail = detail.get("detail", "")
        if isinstance(detail, list):
            detail = str(detail)
        # Pydantic validates min_items=1 before custom validation
        assert "al menos una" in detail.lower() or "at least 1" in detail.lower()

    async def test_create_compra_calculates_monto(self, client: AsyncClient, admin_headers, session):
        """Create purchase calculates monto from costos."""
        from tests.factories import create_proveedor, create_categoria, create_producto
        prov = create_proveedor(session, nombre="ProvMonto")
        cat = create_categoria(session, nombre="CatMonto")
        prod = create_producto(session, nombre="ProdMonto", precio_venta=100, precio_costo=60, stock=10, categorias=[cat], proveedor=prov)
        session.commit()

        resp = await client.post(
            "/compras",
            json={
                "proveedor_id": prov.id,
                "nro_boleta": "BOL-MONTO",
                "detalles": [
                    {"producto_id": prod.id, "cantidad": 3, "costo_unitario": 50},
                    {"producto_id": prod.id, "cantidad": 2},
                ],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["monto"] == 270.0

    async def test_create_compra_pagado_creates_caja_salida(self, client: AsyncClient, admin_headers, session):
        """Create purchase with pagado=true creates caja SALIDA."""
        from tests.factories import create_proveedor, create_categoria, create_producto
        from tests.assertions import assert_caja_movement
        prov = create_proveedor(session, nombre="ProvPagado")
        cat = create_categoria(session, nombre="CatPagado")
        prod = create_producto(session, precio_venta=100, precio_costo=60, stock=10, categorias=[cat], proveedor=prov)
        session.commit()

        resp = await client.post(
            "/compras",
            json={
                "proveedor_id": prov.id,
                "nro_boleta": "BOL-PAGADO",
                "detalles": [{"producto_id": prod.id, "cantidad": 2}],
                "pagado": True,
                "medio_pago": "efectivo",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        compra_id = resp.json()["id"]
        assert_caja_movement(session, "SALIDA", "efectivo", f"Pago {prov.nombre}", 120.0, compra_id=compra_id)

    async def test_create_compra_rejects_pagado_without_medio(self, client: AsyncClient, admin_headers, session):
        """Create purchase with pagado=true but no medio_pago returns 422."""
        from tests.factories import create_proveedor, create_categoria, create_producto
        prov = create_proveedor(session, nombre="ProvNoMedio")
        cat = create_categoria(session, nombre="CatNoMedio")
        prod = create_producto(session, precio_venta=100, precio_costo=60, stock=10, categorias=[cat], proveedor=prov)
        session.commit()

        resp = await client.post(
            "/compras",
            json={
                "proveedor_id": prov.id,
                "nro_boleta": "BOL-NOMEDIO",
                "detalles": [{"producto_id": prod.id, "cantidad": 1}],
                "pagado": True,
            },
            headers=admin_headers,
        )
        assert resp.status_code == 422
        detail = resp.json()
        if isinstance(detail, dict):
            detail = detail.get("detail", "")
        if isinstance(detail, list):
            detail = str(detail)
        assert "medio_pago" in detail.lower()


class TestComprasList:
    """Tests for GET /compras."""

    async def test_list_compras_empty(self, client: AsyncClient, admin_headers):
        """List returns empty when no purchases."""
        resp = await client.get("/compras", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_compras_filters(self, client: AsyncClient, admin_headers, session):
        """List supports filters: fecha, proveedor, pagada, entregada."""
        from tests.factories import create_proveedor, create_categoria, create_producto, create_compra
        from app import models
        from datetime import datetime, timedelta

        prov1 = create_proveedor(session, nombre="ProvList1")
        prov2 = create_proveedor(session, nombre="ProvList2")
        cat = create_categoria(session, nombre="CatList")
        prod = create_producto(session, precio_venta=100, precio_costo=60, stock=100, categorias=[cat], proveedor=prov1)
        yesterday = datetime.utcnow() - timedelta(days=1)
        c1 = create_compra(session, prov1, [{"producto": prod, "cantidad": 1}], fecha_pedido=yesterday)
        c2 = create_compra(session, prov1, [{"producto": prod, "cantidad": 1}], pagado=True, medio_pago=models.MetodoPago.efectivo)
        # c3 with different date (2 days ago)
        c3 = create_compra(session, prov2, [{"producto": prod, "cantidad": 1}], fecha_pedido=datetime.utcnow() - timedelta(days=2))
        c3.fecha_entrega = datetime.utcnow()
        session.add(c3)
        session.commit()

        resp = await client.get("/compras", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        resp = await client.get(f"/compras?fecha={today_str}", headers=admin_headers)
        # c2 has today's date
        assert len(resp.json()) == 1

        resp = await client.get(f"/compras?proveedor={prov1.id}", headers=admin_headers)
        assert len(resp.json()) == 2

        resp = await client.get("/compras?pagada=true", headers=admin_headers)
        assert len(resp.json()) == 1
        assert resp.json()[0]["pagado"] is True

        resp = await client.get("/compras?entregada=true", headers=admin_headers)
        assert len(resp.json()) == 1
        assert resp.json()[0]["entregada"] is True


class TestComprasGet:
    """Tests for GET /compras/{id}."""

    async def test_get_compra_by_id(self, client: AsyncClient, admin_headers, session):
        """Get purchase by ID with details."""
        from tests.factories import create_proveedor, create_categoria, create_producto, create_compra
        prov = create_proveedor(session, nombre="ProvGet")
        cat = create_categoria(session, nombre="CatGet")
        prod = create_producto(session, precio_venta=100, precio_costo=60, stock=10, categorias=[cat], proveedor=prov)
        comp = create_compra(session, prov, [{"producto": prod, "cantidad": 2}])
        session.commit()

        resp = await client.get(f"/compras/{comp.id}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == comp.id
        assert data["proveedor_nombre"] == "ProvGet"
        assert len(data["detalles"]) == 1
        assert data["detalles"][0]["producto_nombre"] == prod.nombre

    async def test_get_compra_404(self, client: AsyncClient, admin_headers):
        """Get non-existent purchase returns 404."""
        resp = await client.get("/compras/99999", headers=admin_headers)
        assert resp.status_code == 404


class TestComprasUpdate:
    """Tests for PATCH /compras/{id}."""

    async def test_update_compra_before_entrega(self, client: AsyncClient, admin_headers, session):
        """Update purchase before entrega succeeds."""
        from tests.factories import create_proveedor, create_categoria, create_producto, create_compra
        prov = create_proveedor(session, nombre="ProvUpdate")
        cat = create_categoria(session, nombre="CatUpdate")
        prod = create_producto(session, precio_venta=100, precio_costo=60, stock=10, categorias=[cat], proveedor=prov)
        comp = create_compra(session, prov, [{"producto": prod, "cantidad": 1}])
        session.commit()

        resp = await client.patch(
            f"/compras/{comp.id}",
            json={"nro_boleta": "BOL-UPD", "fecha_pedido": "2026-02-01T10:00:00", "medio_pago": "transferencia"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["nro_boleta"] == "BOL-UPD"
        assert data["medio_pago"] == "transferencia"

    async def test_update_compra_detalles_recalculates_monto(self, client: AsyncClient, admin_headers, session):
        """Update purchase detalles recalculates monto."""
        from tests.factories import create_proveedor, create_categoria, create_producto, create_compra
        prov = create_proveedor(session, nombre="ProvUpdMonto")
        cat = create_categoria(session, nombre="CatUpdMonto")
        prod = create_producto(session, precio_venta=100, precio_costo=60, stock=10, categorias=[cat], proveedor=prov)
        comp = create_compra(session, prov, [{"producto": prod, "cantidad": 1}])
        session.commit()

        resp = await client.patch(
            f"/compras/{comp.id}",
            json={"detalles": [{"producto_id": prod.id, "cantidad": 5, "costo_unitario": 55}]},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["monto"] == 275.0

    async def test_update_compra_rejects_detalles_after_entrega(self, client: AsyncClient, admin_headers, session):
        """Update purchase detalles after entrega returns 400."""
        from tests.factories import create_proveedor, create_categoria, create_producto, create_compra
        from datetime import datetime
        prov = create_proveedor(session, nombre="ProvUpdEnt")
        cat = create_categoria(session, nombre="CatUpdEnt")
        prod = create_producto(session, precio_venta=100, precio_costo=60, stock=10, categorias=[cat], proveedor=prov)
        comp = create_compra(session, prov, [{"producto": prod, "cantidad": 1}])
        comp.fecha_entrega = datetime.utcnow()
        session.commit()

        resp = await client.patch(
            f"/compras/{comp.id}",
            json={"detalles": [{"producto_id": prod.id, "cantidad": 2}]},
            headers=admin_headers,
        )
        assert resp.status_code == 400
        assert "ya entregada" in resp.json()["detail"].lower()


class TestComprasEntregar:
    """Tests for PATCH /compras/{id}/entregar."""

    async def test_entregar_compra_marks_fecha_entrega(self, client: AsyncClient, admin_headers, session):
        """Entregar marks fecha_entrega and creates INGRESO stock movements."""
        from tests.factories import create_proveedor, create_categoria, create_producto, create_compra
        from tests.assertions import assert_stock_movement, assert_producto_stock
        from app import models
        prov = create_proveedor(session, nombre="ProvEnt")
        cat = create_categoria(session, nombre="CatEnt")
        prod = create_producto(session, nombre="EntProd", precio_venta=100, precio_costo=60, stock=5, categorias=[cat], proveedor=prov)
        comp = create_compra(session, prov, [{"producto": prod, "cantidad": 3}])
        session.commit()

        assert_producto_stock(session, prod.id, 5)

        resp = await client.patch(f"/compras/{comp.id}/entregar", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["entregada"] is True
        assert data["fecha_entrega"] is not None

        assert_stock_movement(session, prod.id, "INGRESO", 3, 5, 8, compra_id=comp.id)
        assert_producto_stock(session, prod.id, 8)

    async def test_entregar_compra_rejects_already_delivered(self, client: AsyncClient, admin_headers, session):
        """Entregar already delivered returns 400."""
        from tests.factories import create_proveedor, create_categoria, create_producto, create_compra
        from datetime import datetime
        prov = create_proveedor(session, nombre="ProvEnt2")
        cat = create_categoria(session, nombre="CatEnt2")
        prod = create_producto(session, precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        comp = create_compra(session, prov, [{"producto": prod, "cantidad": 1}])
        comp.fecha_entrega = datetime.utcnow()
        session.commit()

        resp = await client.patch(f"/compras/{comp.id}/entregar", headers=admin_headers)
        assert resp.status_code == 400
        assert "ya estaba entregada" in resp.json()["detail"].lower()


class TestComprasPagar:
    """Tests for PATCH /compras/{id}/pagar."""

    async def test_pagar_compra_marks_pagado_creates_caja(self, client: AsyncClient, admin_headers, session):
        """Pagar marks pagado and creates caja SALIDA."""
        from tests.factories import create_proveedor, create_categoria, create_producto, create_compra
        from tests.assertions import assert_caja_movement
        prov = create_proveedor(session, nombre="ProvPagar")
        cat = create_categoria(session, nombre="CatPagar")
        prod = create_producto(session, precio_venta=100, precio_costo=60, stock=10, categorias=[cat], proveedor=prov)
        comp = create_compra(session, prov, [{"producto": prod, "cantidad": 2}], pagado=False)
        session.commit()

        resp = await client.patch(
            f"/compras/{comp.id}/pagar",
            json={"medio_pago": "transferencia"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["pagado"] is True
        assert data["medio_pago"] == "transferencia"

        assert_caja_movement(session, "SALIDA", "transferencia", f"Pago {prov.nombre}", 120.0, compra_id=comp.id)

    async def test_pagar_compra_rejects_already_paid(self, client: AsyncClient, admin_headers, session):
        """Pagar already paid returns 400."""
        from tests.factories import create_proveedor, create_categoria, create_producto, create_compra
        from app import models
        prov = create_proveedor(session, nombre="ProvPaid2")
        cat = create_categoria(session, nombre="CatPaid2")
        prod = create_producto(session, precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        comp = create_compra(session, prov, [{"producto": prod, "cantidad": 1}], pagado=True, medio_pago=models.MetodoPago.efectivo)
        session.commit()

        resp = await client.patch(f"/compras/{comp.id}/pagar", json={"medio_pago": "efectivo"}, headers=admin_headers)
        assert resp.status_code == 400
        assert "ya estaba pagada" in resp.json()["detail"].lower()

    async def test_pagar_compra_requires_medio_pago(self, client: AsyncClient, admin_headers, session):
        """Pagar without medio_pago returns 422."""
        from tests.factories import create_proveedor, create_categoria, create_producto, create_compra
        prov = create_proveedor(session, nombre="ProvNoMedio2")
        cat = create_categoria(session, nombre="CatNoMedio2")
        prod = create_producto(session, precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        comp = create_compra(session, prov, [{"producto": prod, "cantidad": 1}], pagado=False, medio_pago=None)
        session.commit()

        resp = await client.patch(f"/compras/{comp.id}/pagar", json={}, headers=admin_headers)
        assert resp.status_code == 422
        assert "indicar medio_pago" in resp.json()["detail"].lower()


class TestComprasDeudas:
    """Tests for GET /compras/deudas."""

    async def test_deudas_returns_unpaid_per_proveedor(self, client: AsyncClient, admin_headers, session):
        """Deudas returns unpaid purchases per proveedor."""
        from tests.factories import create_proveedor, create_categoria, create_producto, create_compra
        from app import models
        prov1 = create_proveedor(session, nombre="ProvDeuda1")
        prov2 = create_proveedor(session, nombre="ProvDeuda2")
        cat = create_categoria(session, nombre="CatDeuda")
        prod = create_producto(session, precio_venta=100, precio_costo=60, stock=100, categorias=[cat], proveedor=prov1)
        create_compra(session, prov1, [{"producto": prod, "cantidad": 2}], pagado=False)
        create_compra(session, prov1, [{"producto": prod, "cantidad": 1}], pagado=True, medio_pago=models.MetodoPago.efectivo)
        create_compra(session, prov2, [{"producto": prod, "cantidad": 3}], pagado=False)
        session.commit()

        resp = await client.get("/compras/deudas", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        p1 = next(p for p in data if p["nombre"] == "ProvDeuda1")
        p2 = next(p for p in data if p["nombre"] == "ProvDeuda2")
        assert p1["deuda"] == 120.0
        assert p1["pendientes"] == 1
        assert p2["deuda"] == 180.0
        assert p2["pendientes"] == 1


class TestComprasDelete:
    """Tests for DELETE /compras/{id}."""

    async def test_delete_compra_before_entrega_pago(self, client: AsyncClient, admin_headers, session):
        """Delete purchase before entrega and pago succeeds."""
        from tests.factories import create_proveedor, create_categoria, create_producto, create_compra
        from tests.assertions import assert_caja_movement
        from sqlalchemy.orm import Session
        from app import models

        prov = create_proveedor(session, nombre="ProvDel")
        cat = create_categoria(session, nombre="CatDel")
        prod = create_producto(session, precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        comp = create_compra(session, prov, [{"producto": prod, "cantidad": 1}])
        session.commit()

        resp = await client.delete(f"/compras/{comp.id}", headers=admin_headers)
        assert resp.status_code == 204

        assert session.get(models.Compra, comp.id) is None

    async def test_delete_compra_rejects_if_entregada(self, client: AsyncClient, admin_headers, session):
        """Delete purchase if entregada returns 400."""
        from tests.factories import create_proveedor, create_categoria, create_producto, create_compra
        from datetime import datetime
        prov = create_proveedor(session, nombre="ProvDelEnt")
        cat = create_categoria(session, nombre="CatDelEnt")
        prod = create_producto(session, precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        comp = create_compra(session, prov, [{"producto": prod, "cantidad": 1}])
        comp.fecha_entrega = datetime.utcnow()
        session.commit()

        resp = await client.delete(f"/compras/{comp.id}", headers=admin_headers)
        assert resp.status_code == 400
        assert "ya entregada" in resp.json()["detail"].lower()

    async def test_delete_compra_rejects_if_pagada(self, client: AsyncClient, admin_headers, session):
        """Delete purchase if pagada returns 400."""
        from tests.factories import create_proveedor, create_categoria, create_producto, create_compra
        from app import models
        prov = create_proveedor(session, nombre="ProvDelPag")
        cat = create_categoria(session, nombre="CatDelPag")
        prod = create_producto(session, precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        comp = create_compra(session, prov, [{"producto": prod, "cantidad": 1}], pagado=True, medio_pago=models.MetodoPago.efectivo)
        session.commit()

        resp = await client.delete(f"/compras/{comp.id}", headers=admin_headers)
        assert resp.status_code == 400
        assert "ya pagada" in resp.json()["detail"].lower()