"""Tests for clients endpoints."""
import pytest
from httpx import AsyncClient


class TestClientesCreate:
    """Tests for POST /clientes."""

    async def test_create_cliente_valid(self, client: AsyncClient, admin_headers):
        """Create client with valid data."""
        resp = await client.post(
            "/clientes",
            json={"nombre": "Cliente Test", "email": "cliente@test.com", "dni": "12345678"},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] > 0
        assert data["nombre"] == "Cliente Test"
        assert data["email"] == "cliente@test.com"
        assert data["dni"] == "12345678"

    async def test_create_cliente_unique_email(self, client: AsyncClient, admin_headers):
        """Create client with duplicate email returns 400."""
        await client.post(
            "/clientes", json={"nombre": "C1", "email": "dup@test.com", "dni": "11111111"}, headers=admin_headers
        )
        resp = await client.post(
            "/clientes", json={"nombre": "C2", "email": "dup@test.com", "dni": "22222222"}, headers=admin_headers
        )
        assert resp.status_code == 400
        assert "email o dni ya registrado" in resp.json()["detail"].lower()

    async def test_create_cliente_unique_dni(self, client: AsyncClient, admin_headers):
        """Create client with duplicate DNI returns 400."""
        await client.post(
            "/clientes", json={"nombre": "C1", "email": "c1@test.com", "dni": "12345678"}, headers=admin_headers
        )
        resp = await client.post(
            "/clientes", json={"nombre": "C2", "email": "c2@test.com", "dni": "12345678"}, headers=admin_headers
        )
        assert resp.status_code == 400
        assert "email o dni ya registrado" in resp.json()["detail"].lower()

    async def test_create_cliente_requires_auth(self, client: AsyncClient):
        """Create client requires authentication."""
        resp = await client.post("/clientes", json={"nombre": "NoAuth", "email": "na@test.com", "dni": "99999999"})
        assert resp.status_code == 401


class TestClientesList:
    """Tests for GET /clientes."""

    async def test_list_clientes_empty(self, client: AsyncClient, admin_headers):
        """List returns empty when no clients."""
        resp = await client.get("/clientes", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_clientes_with_data(self, client: AsyncClient, admin_headers, session):
        """List returns all clients ordered by name."""
        from tests.factories import create_cliente
        create_cliente(session, nombre="Zebra Cliente", email="z@test.com", dni="11111111")
        create_cliente(session, nombre="Alpha Cliente", email="a@test.com", dni="22222222")
        session.commit()

        resp = await client.get("/clientes", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["nombre"] == "Alpha Cliente"
        assert data[1]["nombre"] == "Zebra Cliente"


class TestClientesGet:
    """Tests for GET /clientes/{id}."""

    async def test_get_cliente_by_id(self, client: AsyncClient, admin_headers, session):
        """Get client by ID returns correct data."""
        from tests.factories import create_cliente
        cli = create_cliente(session, nombre="GetCliente", email="get@test.com", dni="33333333")
        session.commit()

        resp = await client.get(f"/clientes/{cli.id}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == cli.id
        assert data["nombre"] == "GetCliente"
        assert data["email"] == "get@test.com"

    async def test_get_cliente_404(self, client: AsyncClient, admin_headers):
        """Get non-existent client returns 404."""
        resp = await client.get("/clientes/99999", headers=admin_headers)
        assert resp.status_code == 404


class TestClientesPedidos:
    """Tests for GET /clientes/{id}/pedidos."""

    async def test_get_client_orders(self, client: AsyncClient, admin_headers, session):
        """Get client orders with details."""
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto, create_pedido
        cat = create_categoria(session, nombre="CatPed")
        prov = create_proveedor(session, nombre="ProvPed")
        prod1 = create_producto(session, nombre="Prod1", precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        prod2 = create_producto(session, nombre="Prod2", precio_venta=200, stock=5, categorias=[cat], proveedor=prov)
        cli = create_cliente(session, nombre="Cliente Con Pedidos", email="pedidos@test.com", dni="44444444")
        ped1 = create_pedido(session, cli, [{"producto": prod1, "cantidad": 2}])
        ped2 = create_pedido(session, cli, [{"producto": prod2, "cantidad": 1}])
        session.commit()

        resp = await client.get(f"/clientes/{cli.id}/pedidos", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["id"] == ped2.id  # ordered by fecha desc
        assert data[1]["id"] == ped1.id
        assert len(data[0]["detalles"]) == 1
        assert len(data[1]["detalles"]) == 1

    async def test_get_client_orders_404(self, client: AsyncClient, admin_headers):
        """Get orders for non-existent client returns 404."""
        resp = await client.get("/clientes/99999/pedidos", headers=admin_headers)
        assert resp.status_code == 404