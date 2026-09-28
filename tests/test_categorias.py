"""Tests for categories endpoints."""
import pytest
from httpx import AsyncClient


class TestCategoriasCreate:
    """Tests for POST /categorias."""

    async def test_create_categoria_valid(self, client: AsyncClient, admin_headers):
        """Create a category with valid data."""
        resp = await client.post(
            "/categorias",
            json={"nombre": "Alimentos", "descripcion": "Comida para mascotas"},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] > 0
        assert data["nombre"] == "Alimentos"
        assert data["descripcion"] == "Comida para mascotas"

    async def test_create_categoria_unique_nombre(self, client: AsyncClient, admin_headers):
        """Creating duplicate category name returns 400."""
        await client.post("/categorias", json={"nombre": "DupCat"}, headers=admin_headers)
        resp = await client.post("/categorias", json={"nombre": "DupCat"}, headers=admin_headers)
        assert resp.status_code == 400
        assert "ya existe" in resp.json()["detail"].lower()

    async def test_create_categoria_requires_auth(self, client: AsyncClient):
        """Creating category requires authentication."""
        resp = await client.post("/categorias", json={"nombre": "NoAuth"})
        assert resp.status_code == 401

    async def test_create_categoria_vendedor_can_create(self, client: AsyncClient, vendedor_headers):
        """Vendedor can create categories."""
        resp = await client.post(
            "/categorias", json={"nombre": "VendCat"}, headers=vendedor_headers
        )
        assert resp.status_code == 201


class TestCategoriasList:
    """Tests for GET /categorias."""

    async def test_list_categorias_empty(self, client: AsyncClient, admin_headers):
        """List returns empty list when no categories."""
        resp = await client.get("/categorias", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_categorias_with_data(self, client: AsyncClient, admin_headers):
        """List returns all categories ordered by name."""
        await client.post("/categorias", json={"nombre": "Zebra"}, headers=admin_headers)
        await client.post("/categorias", json={"nombre": "Alpha"}, headers=admin_headers)
        resp = await client.get("/categorias", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["nombre"] == "Alpha"
        assert data[1]["nombre"] == "Zebra"


class TestCategoriasGet:
    """Tests for GET /categorias/{id}."""

    async def test_get_categoria_by_id(self, client: AsyncClient, admin_headers):
        """Get category by ID returns correct data."""
        create_resp = await client.post("/categorias", json={"nombre": "GetTest"}, headers=admin_headers)
        cat_id = create_resp.json()["id"]
        resp = await client.get(f"/categorias/{cat_id}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == cat_id
        assert data["nombre"] == "GetTest"

    async def test_get_categoria_404(self, client: AsyncClient, admin_headers):
        """Get non-existent category returns 404."""
        resp = await client.get("/categorias/99999", headers=admin_headers)
        assert resp.status_code == 404
        assert "no encontrada" in resp.json()["detail"].lower()


class TestCategoriasUpdate:
    """Tests for PUT /categorias/{id}."""

    async def test_update_categoria_valid(self, client: AsyncClient, admin_headers):
        """Update category with valid data."""
        create_resp = await client.post("/categorias", json={"nombre": "Original"}, headers=admin_headers)
        cat_id = create_resp.json()["id"]
        resp = await client.put(
            f"/categorias/{cat_id}",
            json={"nombre": "Updated", "descripcion": "New desc"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["nombre"] == "Updated"
        assert data["descripcion"] == "New desc"

    async def test_update_categoria_unique_nombre(self, client: AsyncClient, admin_headers):
        """Update to duplicate name returns 400."""
        await client.post("/categorias", json={"nombre": "Cat1"}, headers=admin_headers)
        create_resp = await client.post("/categorias", json={"nombre": "Cat2"}, headers=admin_headers)
        cat2_id = create_resp.json()["id"]
        resp = await client.put(
            f"/categorias/{cat2_id}", json={"nombre": "Cat1"}, headers=admin_headers
        )
        assert resp.status_code == 400
        assert "ya existe otra" in resp.json()["detail"].lower()

    async def test_update_categoria_404(self, client: AsyncClient, admin_headers):
        """Update non-existent category returns 404."""
        resp = await client.put("/categorias/99999", json={"nombre": "New"}, headers=admin_headers)
        assert resp.status_code == 404


class TestCategoriasDelete:
    """Tests for DELETE /categorias/{id}."""

    async def test_delete_categoria_requires_admin(self, client: AsyncClient, vendedor_headers):
        """Delete requires admin role."""
        create_resp = await client.post("/categorias", json={"nombre": "ToDelete"}, headers=vendedor_headers)
        cat_id = create_resp.json()["id"]
        resp = await client.delete(f"/categorias/{cat_id}", headers=vendedor_headers)
        assert resp.status_code == 403

    async def test_delete_categoria_admin_succeeds(self, client: AsyncClient, admin_headers):
        """Admin can delete category."""
        create_resp = await client.post("/categorias", json={"nombre": "ToDeleteAdmin"}, headers=admin_headers)
        cat_id = create_resp.json()["id"]
        resp = await client.delete(f"/categorias/{cat_id}", headers=admin_headers)
        assert resp.status_code == 204

    async def test_delete_categoria_reassigns_products(self, client: AsyncClient, session, admin_headers):
        """Deleting category reassigns products to no category (orphan)."""
        from app import models
        from tests.factories import create_categoria, create_producto

        cat = create_categoria(session, nombre="ToDelete")
        prod = create_producto(session, nombre="ProdWithCat", categorias=[cat])
        session.commit()

        resp = await client.delete(f"/categorias/{cat.id}", headers=admin_headers)
        assert resp.status_code == 204

        session.expire_all()
        prod_refreshed = session.get(models.Producto, prod.id)
        assert prod_refreshed.categorias == []

    async def test_delete_categoria_404(self, client: AsyncClient, admin_headers):
        """Delete non-existent category returns 404."""
        resp = await client.delete("/categorias/99999", headers=admin_headers)
        assert resp.status_code == 404