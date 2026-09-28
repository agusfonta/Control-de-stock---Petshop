"""Tests for products endpoints."""
import pytest
from httpx import AsyncClient


class TestProductosCreate:
    """Tests for POST /productos."""

    async def test_create_producto_minimal(self, client: AsyncClient, admin_headers, session):
        """Create product with minimal required fields."""
        from tests.factories import create_categoria, create_proveedor
        cat = create_categoria(session, nombre="Cat1")
        prov = create_proveedor(session, nombre="Prov1")
        session.commit()

        resp = await client.post(
            "/productos",
            json={
                "nombre": "Prod Test",
                "precio_costo": 50.0,
                "precio_venta": 100.0,
                "stock": 0,
                "categoria_ids": [cat.id],
                "proveedor_id": prov.id,
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] > 0
        assert data["nombre"] == "Prod Test"
        assert data["precio_venta"] == 100.0
        assert data["stock"] == 0
        assert data["activo"] is True

    async def test_create_producto_all_fields(self, client: AsyncClient, admin_headers, session):
        """Create product with all optional fields."""
        from tests.factories import create_categoria, create_proveedor
        cat = create_categoria(session, nombre="CatFull")
        prov = create_proveedor(session, nombre="ProvFull")
        prov2 = create_proveedor(session, nombre="ProvAlt")
        session.commit()

        resp = await client.post(
            "/productos",
            json={
                "sku": "FULL-001",
                "nombre": "Full Product",
                "descripcion": "Description",
                "marca": "Marca",
                "unidad": "unidad",
                "precio_costo": 50.0,
                "precio_venta": 150.0,
                "stock": 20,
                "stock_minimo": 5,
                "imagen_url": "https://example.com/img.jpg",
                "activo": True,
                "categoria_ids": [cat.id],
                "proveedor_id": prov.id,
                "proveedor_ids_alt": [prov.id, prov2.id],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["sku"] == "FULL-001"
        assert data["proveedor_nombre"] == "ProvFull"
        assert set(data["proveedor_ids_alt"]) == {prov.id, prov2.id}
        assert len(data["categorias"]) == 1

    async def test_create_producto_duplicate_sku(self, client: AsyncClient, admin_headers, session):
        """Create product with duplicate SKU returns 400."""
        from tests.factories import create_categoria, create_proveedor
        cat = create_categoria(session, nombre="CatSKU")
        prov = create_proveedor(session, nombre="ProvSKU")
        session.commit()

        await client.post(
            "/productos",
            json={"nombre": "Prod1", "precio_costo": 50, "precio_venta": 100, "stock": 10, "sku": "DUP-SKU", "categoria_ids": [cat.id], "proveedor_id": prov.id},
            headers=admin_headers,
        )
        resp = await client.post(
            "/productos",
            json={"nombre": "Prod2", "precio_costo": 50, "precio_venta": 200, "stock": 10, "sku": "DUP-SKU", "categoria_ids": [cat.id], "proveedor_id": prov.id},
            headers=admin_headers,
        )
        assert resp.status_code == 400
        assert "sku ya existe" in resp.json()["detail"].lower()

    async def test_create_producto_precio_venta_gt_zero(self, client: AsyncClient, admin_headers, session):
        """precio_venta must be > 0."""
        from tests.factories import create_categoria, create_proveedor
        cat = create_categoria(session, nombre="CatPrice")
        prov = create_proveedor(session, nombre="ProvPrice")
        session.commit()

        resp = await client.post(
            "/productos",
            json={"nombre": "BadPrice", "precio_costo": 50, "precio_venta": 0, "stock": 10, "categoria_ids": [cat.id], "proveedor_id": prov.id},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    async def test_create_producto_imagen_url_valid(self, client: AsyncClient, admin_headers, session):
        """imagen_url must be valid http(s) URL."""
        from tests.factories import create_categoria, create_proveedor
        cat = create_categoria(session, nombre="CatURL")
        prov = create_proveedor(session, nombre="ProvURL")
        session.commit()

        resp = await client.post(
            "/productos",
            json={"nombre": "BadURL", "precio_costo": 50, "precio_venta": 100, "stock": 10, "imagen_url": "ftp://bad.com", "categoria_ids": [cat.id], "proveedor_id": prov.id},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    async def test_create_producto_categoria_ids_exist(self, client: AsyncClient, admin_headers, session):
        """All categoria_ids must exist."""
        from tests.factories import create_categoria, create_proveedor
        cat = create_categoria(session, nombre="CatExist")
        prov = create_proveedor(session, nombre="ProvExist")
        session.commit()

        resp = await client.post(
            "/productos",
            json={"nombre": "BadCat", "precio_costo": 50, "precio_venta": 100, "stock": 10, "categoria_ids": [99999], "proveedor_id": prov.id},
            headers=admin_headers,
        )
        assert resp.status_code == 400
        assert "categorias no existen" in resp.json()["detail"].lower()

    async def test_create_producto_proveedor_ids_exist(self, client: AsyncClient, admin_headers, session):
        """proveedor_id and proveedor_ids_alt must exist."""
        from tests.factories import create_categoria, create_proveedor
        cat = create_categoria(session, nombre="CatProv")
        prov = create_proveedor(session, nombre="ProvExist")
        session.commit()

        resp = await client.post(
            "/productos",
            json={"nombre": "BadProv", "precio_costo": 50, "precio_venta": 100, "stock": 10, "categoria_ids": [cat.id], "proveedor_id": 99999},
            headers=admin_headers,
        )
        assert resp.status_code == 400
        assert "proveedor principal no existe" in resp.json()["detail"].lower()

    async def test_create_producto_proveedor_id_in_alts(self, client: AsyncClient, admin_headers, session):
        """proveedor_id must be in proveedor_ids_alt if provided."""
        from tests.factories import create_categoria, create_proveedor
        cat = create_categoria(session, nombre="CatAlt")
        prov1 = create_proveedor(session, nombre="Prov1")
        prov2 = create_proveedor(session, nombre="Prov2")
        session.commit()

        resp = await client.post(
            "/productos",
            json={"nombre": "BadAlt", "precio_costo": 50, "precio_venta": 100, "stock": 10, "categoria_ids": [cat.id], "proveedor_id": prov1.id, "proveedor_ids_alt": [prov2.id]},
            headers=admin_headers,
        )
        assert resp.status_code == 400
        assert "proveedor principal debe estar entre los alternativos" in resp.json()["detail"].lower()


class TestProductosList:
    """Tests for GET /productos."""

    async def test_list_productos_empty(self, client: AsyncClient, admin_headers):
        """List returns empty when no products."""
        resp = await client.get("/productos", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_productos_filter_categoria(self, client: AsyncClient, admin_headers, session):
        """Filter by categoria_id."""
        from tests.factories import create_categoria, create_proveedor, create_producto
        cat1 = create_categoria(session, nombre="CatList1")
        cat2 = create_categoria(session, nombre="CatList2")
        prov = create_proveedor(session, nombre="ProvList")
        p1 = create_producto(session, nombre="P1", categorias=[cat1], proveedor=prov)
        p2 = create_producto(session, nombre="P2", categorias=[cat2], proveedor=prov)
        session.commit()

        resp = await client.get(f"/productos?categoria={cat1.id}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["nombre"] == "P1"

    async def test_list_productos_filter_search(self, client: AsyncClient, admin_headers, session):
        """Filter by search term on nombre/marca."""
        from tests.factories import create_categoria, create_proveedor, create_producto
        cat = create_categoria(session, nombre="CatSearch")
        prov = create_proveedor(session, nombre="ProvSearch")
        create_producto(session, nombre="Alimento Perro", marca="MarcaA", categorias=[cat], proveedor=prov)
        create_producto(session, nombre="Juguete Gato", marca="MarcaB", categorias=[cat], proveedor=prov)
        session.commit()

        resp = await client.get("/productos?search=Perro", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["nombre"] == "Alimento Perro"

    async def test_list_productos_stock_bajo(self, client: AsyncClient, admin_headers, session):
        """Filter stock_bajo returns products with stock <= stock_minimo."""
        from tests.factories import create_categoria, create_proveedor, create_producto
        cat = create_categoria(session, nombre="CatStock")
        prov = create_proveedor(session, nombre="ProvStock")
        create_producto(session, nombre="LowStock", stock=2, stock_minimo=5, categorias=[cat], proveedor=prov)
        create_producto(session, nombre="NormalStock", stock=20, stock_minimo=5, categorias=[cat], proveedor=prov)
        session.commit()

        resp = await client.get("/productos?stock_bajo=true", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["nombre"] == "LowStock"
        assert data[0]["stock_bajo"] is True

    async def test_list_productos_solo_activos(self, client: AsyncClient, admin_headers, session):
        """Filter solo_activos returns only active products."""
        from tests.factories import create_categoria, create_proveedor, create_producto
        cat = create_categoria(session, nombre="CatActive")
        prov = create_proveedor(session, nombre="ProvActive")
        create_producto(session, nombre="ActiveProd", activo=True, categorias=[cat], proveedor=prov)
        create_producto(session, nombre="InactiveProd", activo=False, categorias=[cat], proveedor=prov)
        session.commit()

        resp = await client.get("/productos?solo_activos=true", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["nombre"] == "ActiveProd"

    async def test_list_productos_filter_proveedor(self, client: AsyncClient, admin_headers, session):
        """Filter by proveedor (main or alt)."""
        from tests.factories import create_categoria, create_proveedor, create_producto
        cat = create_categoria(session, nombre="CatProvFilter")
        prov1 = create_proveedor(session, nombre="ProvFilter1")
        prov2 = create_proveedor(session, nombre="ProvFilter2")
        create_producto(session, nombre="PMain1", proveedor=prov1, categorias=[cat])
        create_producto(session, nombre="PAlt1", proveedor=prov1, proveedores_alt=[prov2], categorias=[cat])
        create_producto(session, nombre="PMain2", proveedor=prov2, categorias=[cat])
        session.commit()

        resp = await client.get(f"/productos?proveedor={prov1.id}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = {p["nombre"] for p in data}
        assert names == {"PMain1", "PAlt1"}


class TestProductosGet:
    """Tests for GET /productos/{id}."""

    async def test_get_producto_with_relations(self, client: AsyncClient, admin_headers, session):
        """Get product includes relations."""
        from tests.factories import create_categoria, create_proveedor, create_producto
        cat = create_categoria(session, nombre="CatGet")
        prov = create_proveedor(session, nombre="ProvGet")
        prov2 = create_proveedor(session, nombre="ProvAltGet")
        prod = create_producto(session, nombre="GetProd", categorias=[cat], proveedor=prov, proveedores_alt=[prov2])
        session.commit()

        resp = await client.get(f"/productos/{prod.id}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == prod.id
        assert len(data["categorias"]) == 1
        assert data["proveedor_nombre"] == "ProvGet"
        assert prov2.id in data["proveedor_ids_alt"]

    async def test_get_producto_404(self, client: AsyncClient, admin_headers):
        """Get non-existent product returns 404."""
        resp = await client.get("/productos/99999", headers=admin_headers)
        assert resp.status_code == 404


class TestProductosUpdate:
    """Tests for PATCH /productos/{id}."""

    async def test_update_producto_partial(self, client: AsyncClient, admin_headers, session):
        """Partial update works."""
        from tests.factories import create_categoria, create_proveedor, create_producto
        cat = create_categoria(session, nombre="CatUpd")
        prov = create_proveedor(session, nombre="ProvUpd")
        prod = create_producto(session, nombre="Orig", precio_venta=100, categorias=[cat], proveedor=prov)
        session.commit()

        resp = await client.patch(
            f"/productos/{prod.id}",
            json={"nombre": "Updated", "precio_venta": 150},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["nombre"] == "Updated"
        assert data["precio_venta"] == 150
        assert data["descripcion"] is None

    async def test_update_producto_sku_unique(self, client: AsyncClient, admin_headers, session):
        """Update SKU to existing returns 400."""
        from tests.factories import create_categoria, create_proveedor, create_producto
        cat = create_categoria(session, nombre="CatSKUUpd")
        prov = create_proveedor(session, nombre="ProvSKUUpd")
        p1 = create_producto(session, sku="SKU1", categorias=[cat], proveedor=prov)
        p2 = create_producto(session, sku="SKU2", categorias=[cat], proveedor=prov)
        session.commit()

        resp = await client.patch(
            f"/productos/{p2.id}", json={"sku": "SKU1"}, headers=admin_headers
        )
        assert resp.status_code == 400
        assert "sku ya existe en otro producto" in resp.json()["detail"].lower()

    async def test_update_producto_categoria_ids_replacement(self, client: AsyncClient, admin_headers, session):
        """Update categoria_ids replaces all categories."""
        from tests.factories import create_categoria, create_proveedor, create_producto
        cat1 = create_categoria(session, nombre="CatOld")
        cat2 = create_categoria(session, nombre="CatNew")
        prov = create_proveedor(session, nombre="ProvCatUpd")
        prod = create_producto(session, categorias=[cat1], proveedor=prov)
        session.commit()

        resp = await client.patch(
            f"/productos/{prod.id}", json={"categoria_ids": [cat2.id]}, headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["categorias"]) == 1
        assert data["categorias"][0]["id"] == cat2.id

    async def test_update_producto_proveedor_changes(self, client: AsyncClient, admin_headers, session):
        """Update proveedor_id and proveedor_ids_alt."""
        from tests.factories import create_categoria, create_proveedor, create_producto
        cat = create_categoria(session, nombre="CatProvUpd")
        prov1 = create_proveedor(session, nombre="ProvOld")
        prov2 = create_proveedor(session, nombre="ProvNew")
        prov3 = create_proveedor(session, nombre="ProvAltNew")
        prod = create_producto(session, proveedor=prov1, categorias=[cat])
        session.commit()

        resp = await client.patch(
            f"/productos/{prod.id}",
            json={"proveedor_id": prov2.id, "proveedor_ids_alt": [prov2.id, prov3.id]},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["proveedor_id"] == prov2.id
        assert set(data["proveedor_ids_alt"]) == {prov2.id, prov3.id}


class TestProductosDelete:
    """Tests for DELETE /productos/{id}."""

    async def test_delete_producto_requires_admin(self, client: AsyncClient, vendedor_headers, session):
        """Delete requires admin."""
        from tests.factories import create_categoria, create_proveedor, create_producto
        cat = create_categoria(session, nombre="CatDel")
        prov = create_proveedor(session, nombre="ProvDel")
        prod = create_producto(session, categorias=[cat], proveedor=prov)
        session.commit()

        resp = await client.delete(f"/productos/{prod.id}", headers=vendedor_headers)
        assert resp.status_code == 403

    async def test_delete_producto_with_ventas_returns_400(self, client: AsyncClient, admin_headers, session):
        """Delete product with sales returns 400."""
        from tests.factories import create_categoria, create_proveedor, create_producto, create_cliente, create_pedido
        cat = create_categoria(session, nombre="CatDelVenta")
        prov = create_proveedor(session, nombre="ProvDelVenta")
        prod = create_producto(session, nombre="WithVentas", stock=10, categorias=[cat], proveedor=prov)
        cli = create_cliente(session, nombre="CliVenta")
        create_pedido(session, cli, [{"producto": prod, "cantidad": 1}])
        session.commit()

        resp = await client.delete(f"/productos/{prod.id}", headers=admin_headers)
        assert resp.status_code == 400
        assert "tiene ventas asociadas" in resp.json()["detail"].lower()

    async def test_delete_producto_without_ventas_succeeds(self, client: AsyncClient, admin_headers, session):
        """Delete product without sales succeeds."""
        from tests.factories import create_categoria, create_proveedor, create_producto
        cat = create_categoria(session, nombre="CatDelOk")
        prov = create_proveedor(session, nombre="ProvDelOk")
        prod = create_producto(session, categorias=[cat], proveedor=prov)
        session.commit()

        resp = await client.delete(f"/productos/{prod.id}", headers=admin_headers)
        assert resp.status_code == 204


class TestProductosImportCSV:
    """Tests for POST /productos/import-csv."""

    async def test_import_csv_creates_products_and_categories(self, client: AsyncClient, admin_headers, session):
        """Import CSV creates products and auto-creates categories."""
        from tests.factories import create_proveedor
        prov = create_proveedor(session, nombre="ProvCSV")
        session.commit()

        csv_content = "sku,nombre,precio_venta,categorias\nCSV-001,CSV Product 1,100,Alimentos\nCSV-002,CSV Product 2,200,Accesorios|Juguetes\n"
        files = {"file": ("import.csv", csv_content, "text/csv")}
        resp = await client.post("/productos/import-csv", files=files, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["creados"] == 2
        assert set(data["categorias_creadas"]) == {"Alimentos", "Accesorios", "Juguetes"}

    async def test_import_csv_validates_rows(self, client: AsyncClient, admin_headers, session):
        """Import CSV validates each row, rolls back on error."""
        from tests.factories import create_proveedor
        prov = create_proveedor(session, nombre="ProvCSVVal")
        session.commit()

        csv_content = "sku,nombre,precio_venta\nBAD,Bad Product,-10\n"
        files = {"file": ("import.csv", csv_content, "text/csv")}
        resp = await client.post("/productos/import-csv", files=files, headers=admin_headers)
        assert resp.status_code == 400
        assert "precio_venta debe ser" in resp.json()["detail"]

    async def test_import_csv_requires_min_columns(self, client: AsyncClient, admin_headers):
        """Import CSV requires nombre and precio_venta columns."""
        csv_content = "sku,descripcion\nX,Desc\n"
        files = {"file": ("import.csv", csv_content, "text/csv")}
        resp = await client.post("/productos/import-csv", files=files, headers=admin_headers)
        assert resp.status_code == 400
        assert "columnas mínimas" in resp.json()["detail"]