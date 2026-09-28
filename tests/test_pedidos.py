"""Tests for orders endpoints."""
import pytest
from httpx import AsyncClient


class TestPedidosCreate:
    """Tests for POST /pedidos."""

    async def test_create_pedido_valid(self, client: AsyncClient, admin_headers, session):
        """Create order with valid data."""
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto
        cat = create_categoria(session, nombre="CatPed")
        prov = create_proveedor(session, nombre="ProvPed")
        prod = create_producto(session, nombre="Prod1", precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        cli = create_cliente(session, nombre="Cli1", email="cli1@test.com", dni="11111111")
        session.commit()

        resp = await client.post(
            "/pedidos",
            json={
                "cliente_id": cli.id,
                "metodo_pago": "efectivo",
                "detalles": [{"producto_id": prod.id, "cantidad": 2}],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] > 0
        assert data["cliente_id"] == cli.id
        assert data["estado"] == "pagado"
        assert data["metodo_pago"] == "efectivo"
        assert len(data["detalles"]) == 1
        assert data["detalles"][0]["cantidad"] == 2
        assert data["detalles"][0]["precio_unitario"] == 100
        assert data["total"] == 200

    async def test_create_pedido_client_exists(self, client: AsyncClient, admin_headers):
        """Create order with non-existent client returns 404."""
        resp = await client.post(
            "/pedidos",
            json={
                "cliente_id": 99999,
                "metodo_pago": "efectivo",
                "detalles": [{"producto_id": 1, "cantidad": 1}],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 404
        assert "cliente no existe" in resp.json()["detail"].lower()

    async def test_create_pedido_producto_exists(self, client: AsyncClient, admin_headers, session):
        """Create order with non-existent product returns 404."""
        from tests.factories import create_cliente
        cli = create_cliente(session, nombre="CliProd", email="prod@test.com", dni="22222222")
        session.commit()

        resp = await client.post(
            "/pedidos",
            json={
                "cliente_id": cli.id,
                "metodo_pago": "efectivo",
                "detalles": [{"producto_id": 99999, "cantidad": 1}],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 404
        assert "producto" in resp.json()["detail"].lower()

    async def test_create_pedido_producto_activo(self, client: AsyncClient, admin_headers, session):
        """Create order with inactive product returns 422."""
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto
        cat = create_categoria(session, nombre="CatInactive")
        prov = create_proveedor(session, nombre="ProvInactive")
        prod = create_producto(session, nombre="InactiveProd", precio_venta=100, stock=10, activo=False, categorias=[cat], proveedor=prov)
        cli = create_cliente(session, nombre="CliInactive", email="inactive@test.com", dni="33333333")
        session.commit()

        resp = await client.post(
            "/pedidos",
            json={
                "cliente_id": cli.id,
                "metodo_pago": "efectivo",
                "detalles": [{"producto_id": prod.id, "cantidad": 1}],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 422
        assert "inactivo" in resp.json()["detail"].lower()

    async def test_create_pedido_precio_venta_gt_zero(self, client: AsyncClient, admin_headers, session):
        """Create order with zero-price product returns 422."""
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto
        cat = create_categoria(session, nombre="CatZeroPrice")
        prov = create_proveedor(session, nombre="ProvZeroPrice")
        prod = create_producto(session, nombre="ZeroPrice", precio_venta=0, stock=10, categorias=[cat], proveedor=prov)
        cli = create_cliente(session, nombre="CliZero", email="zero@test.com", dni="44444444")
        session.commit()

        resp = await client.post(
            "/pedidos",
            json={
                "cliente_id": cli.id,
                "metodo_pago": "efectivo",
                "detalles": [{"producto_id": prod.id, "cantidad": 1}],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 422
        assert "precio 0" in resp.json()["detail"].lower()

    async def test_create_pedido_stock_sufficient(self, client: AsyncClient, admin_headers, session):
        """Create order with insufficient stock returns 422."""
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto
        cat = create_categoria(session, nombre="CatStock")
        prov = create_proveedor(session, nombre="ProvStock")
        prod = create_producto(session, nombre="LowStock", precio_venta=100, stock=2, categorias=[cat], proveedor=prov)
        cli = create_cliente(session, nombre="CliStock", email="stock@test.com", dni="55555555")
        session.commit()

        resp = await client.post(
            "/pedidos",
            json={
                "cliente_id": cli.id,
                "metodo_pago": "efectivo",
                "detalles": [{"producto_id": prod.id, "cantidad": 5}],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 422
        assert "stock insuficiente" in resp.json()["detail"].lower()

    async def test_create_pedido_creates_movimiento_stock(self, client: AsyncClient, admin_headers, session):
        """Create order creates MovimientoStock EGRESO_VENTA per line."""
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto
        from tests.assertions import assert_stock_movement, assert_producto_stock
        cat = create_categoria(session, nombre="CatMov")
        prov = create_proveedor(session, nombre="ProvMov")
        prod = create_producto(session, nombre="MovProd", precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        cli = create_cliente(session, nombre="CliMov", email="mov@test.com", dni="66666666")
        session.commit()

        resp = await client.post(
            "/pedidos",
            json={
                "cliente_id": cli.id,
                "metodo_pago": "efectivo",
                "detalles": [{"producto_id": prod.id, "cantidad": 3}],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        pedido_id = resp.json()["id"]

        assert_stock_movement(session, prod.id, "EGRESO_VENTA", 3, 10, 7, pedido_id=pedido_id)
        assert_producto_stock(session, prod.id, 7)

    async def test_create_pedido_creates_movimiento_caja(self, client: AsyncClient, admin_headers, session):
        """Create order creates MovimientoCaja ENTRADA."""
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto
        from tests.assertions import assert_caja_movement
        cat = create_categoria(session, nombre="CatCaja")
        prov = create_proveedor(session, nombre="ProvCaja")
        prod = create_producto(session, nombre="CajaProd", precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        cli = create_cliente(session, nombre="CliCaja", email="caja@test.com", dni="77777777")
        session.commit()

        resp = await client.post(
            "/pedidos",
            json={
                "cliente_id": cli.id,
                "metodo_pago": "efectivo",
                "detalles": [{"producto_id": prod.id, "cantidad": 2}],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        pedido_id = resp.json()["id"]
        total = 200.0

        assert_caja_movement(session, "ENTRADA", "efectivo", f"Venta #{pedido_id}", total, pedido_id=pedido_id)

    async def test_create_pedido_line_discounts(self, client: AsyncClient, admin_headers, session):
        """Create order with line discounts (porcentaje, monto_fijo, limits)."""
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto
        cat = create_categoria(session, nombre="CatDisc")
        prov = create_proveedor(session, nombre="ProvDisc")
        prod = create_producto(session, nombre="DiscProd", precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        cli = create_cliente(session, nombre="CliDisc", email="disc@test.com", dni="88888888")
        session.commit()

        # porcentaje
        resp = await client.post(
            "/pedidos",
            json={
                "cliente_id": cli.id,
                "metodo_pago": "efectivo",
                "detalles": [{"producto_id": prod.id, "cantidad": 1, "descuento_tipo": "porcentaje", "descuento_valor": 10}],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["detalles"][0]["subtotal_linea"] == 90.0

        # monto_fijo
        resp = await client.post(
            "/pedidos",
            json={
                "cliente_id": cli.id,
                "metodo_pago": "efectivo",
                "detalles": [{"producto_id": prod.id, "cantidad": 1, "descuento_tipo": "monto_fijo", "descuento_valor": 20}],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["detalles"][0]["subtotal_linea"] == 80.0

        # reject > base
        resp = await client.post(
            "/pedidos",
            json={
                "cliente_id": cli.id,
                "metodo_pago": "efectivo",
                "detalles": [{"producto_id": prod.id, "cantidad": 1, "descuento_tipo": "monto_fijo", "descuento_valor": 150}],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 422

    async def test_create_pedido_order_discounts(self, client: AsyncClient, admin_headers, session):
        """Create order with order-level discounts."""
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto
        cat = create_categoria(session, nombre="CatOrdDisc")
        prov = create_proveedor(session, nombre="ProvOrdDisc")
        prod = create_producto(session, nombre="OrdDiscProd", precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        cli = create_cliente(session, nombre="CliOrdDisc", email="odisc@test.com", dni="99999999")
        session.commit()

        resp = await client.post(
            "/pedidos",
            json={
                "cliente_id": cli.id,
                "metodo_pago": "efectivo",
                "descuento_tipo": "porcentaje",
                "descuento_valor": 10,
                "detalles": [{"producto_id": prod.id, "cantidad": 2}],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["subtotal"] == 200.0
        assert data["total"] == 180.0


class TestPedidosList:
    """Tests for GET /pedidos."""

    async def test_list_pedidos_empty(self, client: AsyncClient, admin_headers):
        """List returns empty when no orders."""
        resp = await client.get("/pedidos", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_pedidos_filter_fecha(self, client: AsyncClient, admin_headers, session):
        """Filter orders by fecha (single day)."""
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto, create_pedido
        from datetime import datetime, timedelta
        cat = create_categoria(session, nombre="CatFecha")
        prov = create_proveedor(session, nombre="ProvFecha")
        prod = create_producto(session, precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        cli = create_cliente(session, nombre="CliFecha", email="fecha@test.com", dni="10101010")
        yesterday = datetime.utcnow() - timedelta(days=1)
        create_pedido(session, cli, [{"producto": prod, "cantidad": 1}], fecha=yesterday)
        create_pedido(session, cli, [{"producto": prod, "cantidad": 1}])
        session.commit()

        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        resp = await client.get(f"/pedidos?fecha={today_str}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

    async def test_list_pedidos_filter_desde_hasta(self, client: AsyncClient, admin_headers, session):
        """Filter orders by desde and hasta date range."""
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto, create_pedido
        from datetime import datetime, timedelta
        cat = create_categoria(session, nombre="CatRange")
        prov = create_proveedor(session, nombre="ProvRange")
        prod = create_producto(session, precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        cli = create_cliente(session, nombre="CliRange", email="range@test.com", dni="11111112")
        three_days_ago = datetime.utcnow() - timedelta(days=3)
        two_days_ago = datetime.utcnow() - timedelta(days=2)
        create_pedido(session, cli, [{"producto": prod, "cantidad": 1}], fecha=three_days_ago)
        create_pedido(session, cli, [{"producto": prod, "cantidad": 1}], fecha=two_days_ago)
        create_pedido(session, cli, [{"producto": prod, "cantidad": 1}])
        session.commit()

        desde = (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%d")
        hasta = datetime.utcnow().strftime("%Y-%m-%d")
        resp = await client.get(f"/pedidos?desde={desde}&hasta={hasta}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2


class TestPedidosGet:
    """Tests for GET /pedidos/{id}."""

    async def test_get_pedido_by_id(self, client: AsyncClient, admin_headers, session):
        """Get order by ID with details."""
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto, create_pedido
        cat = create_categoria(session, nombre="CatGet")
        prov = create_proveedor(session, nombre="ProvGet")
        prod = create_producto(session, precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        cli = create_cliente(session, nombre="CliGet", email="get@test.com", dni="12121212")
        ped = create_pedido(session, cli, [{"producto": prod, "cantidad": 2}])
        session.commit()

        resp = await client.get(f"/pedidos/{ped.id}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == ped.id
        assert len(data["detalles"]) == 1

    async def test_get_pedido_404(self, client: AsyncClient, admin_headers):
        """Get non-existent order returns 404."""
        resp = await client.get("/pedidos/99999", headers=admin_headers)
        assert resp.status_code == 404


class TestPedidosCancel:
    """Tests for PATCH /pedidos/{id}/cancelar."""

    async def test_cancel_pedido_404(self, client: AsyncClient, admin_headers):
        """Cancel non-existent order returns 404."""
        resp = await client.patch("/pedidos/99999/cancelar", headers=admin_headers)
        assert resp.status_code == 404

    async def test_cancel_pedido_already_cancelled(self, client: AsyncClient, admin_headers, session):
        """Cancel already cancelled order returns 400."""
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto, create_pedido
        from app.models import EstadoPedido
        cat = create_categoria(session, nombre="CatCancel")
        prov = create_proveedor(session, nombre="ProvCancel")
        prod = create_producto(session, precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        cli = create_cliente(session, nombre="CliCancel", email="cancel@test.com", dni="13131313")
        ped = create_pedido(session, cli, [{"producto": prod, "cantidad": 1}])
        ped.estado = EstadoPedido.cancelado
        session.commit()

        resp = await client.patch(f"/pedidos/{ped.id}/cancelar", headers=admin_headers)
        assert resp.status_code == 400
        assert "ya cancelado" in resp.json()["detail"].lower()

    async def test_cancel_pedido_returns_stock(self, client: AsyncClient, admin_headers, session):
        """Cancel order returns stock and creates DEVOLUCION_CANCEL movements."""
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto, create_pedido
        from tests.assertions import assert_stock_movement, assert_producto_stock
        cat = create_categoria(session, nombre="CatCancelStock")
        prov = create_proveedor(session, nombre="ProvCancelStock")
        prod = create_producto(session, precio_venta=100, stock=5, categorias=[cat], proveedor=prov)
        cli = create_cliente(session, nombre="CliCancelStock", email="cstock@test.com", dni="14141414")
        ped = create_pedido(session, cli, [{"producto": prod, "cantidad": 2}])
        session.commit()

        assert_producto_stock(session, prod.id, 3)

        resp = await client.patch(f"/pedidos/{ped.id}/cancelar", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["estado"] == "cancelado"

        assert_stock_movement(session, prod.id, "DEVOLUCION_CANCEL", 2, 3, 5, pedido_id=ped.id)
        assert_producto_stock(session, prod.id, 5)

    async def test_cancel_pedido_creates_movimiento_caja_salida(self, client: AsyncClient, admin_headers, session):
        """Cancel order creates MovimientoCaja SALIDA."""
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto, create_pedido
        from tests.assertions import assert_caja_movement
        cat = create_categoria(session, nombre="CatCancelCaja")
        prov = create_proveedor(session, nombre="ProvCancelCaja")
        prod = create_producto(session, precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        cli = create_cliente(session, nombre="CliCancelCaja", email="ccaja@test.com", dni="15151515")
        ped = create_pedido(session, cli, [{"producto": prod, "cantidad": 1}])
        session.commit()

        resp = await client.patch(f"/pedidos/{ped.id}/cancelar", headers=admin_headers)
        assert resp.status_code == 200

        assert_caja_movement(session, "SALIDA", "efectivo", f"Anulación venta #{ped.id}", ped.total, pedido_id=ped.id)


class TestPedidosPagoMultiple:
    """Tests for POST /pedidos with pagos (pago mixto)."""

    async def _setup_1000(self, session, nombre=None):
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto
        cat = create_categoria(session)
        prov = create_proveedor(session)
        prod = create_producto(session, precio_venta=1000, stock=10, categorias=[cat], proveedor=prov)
        cli = create_cliente(session, **({"nombre": nombre} if nombre else {}))
        session.commit()
        return prod, cli

    async def test_create_pedido_pago_mixto(self, client: AsyncClient, admin_headers, session):
        """Mixto válido: 201, desglose, es_mixto, stock y 2 ENTRADAs."""
        from tests.assertions import assert_caja_movement, assert_producto_stock
        prod, cli = await self._setup_1000(session)

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
        data = resp.json()
        assert data["total"] == 1000.0
        assert data["es_mixto"] is True
        assert len(data["pagos"]) == 2
        assert {(p["metodo"], p["monto"]) for p in data["pagos"]} == {("efectivo", 600.0), ("debito", 400.0)}
        assert data["metodo_pago"] == "efectivo"
        assert_producto_stock(session, prod.id, 9)

        assert_caja_movement(session, "ENTRADA", "efectivo", f"Venta #{data['id']}", 600.0, pedido_id=data["id"])
        assert_caja_movement(session, "ENTRADA", "debito", f"Venta #{data['id']}", 400.0, pedido_id=data["id"])

        get = await client.get(f"/pedidos/{data['id']}", headers=admin_headers)
        assert get.status_code == 200
        assert get.json()["es_mixto"] is True
        assert len(get.json()["pagos"]) == 2

    async def test_create_pedido_pagos_un_solo_pago_en_lista(self, client: AsyncClient, admin_headers, session):
        """Un solo pago en lista: 201 y es_mixto False."""
        prod, cli = await self._setup_1000(session)

        resp = await client.post(
            "/pedidos",
            json={
                "cliente_id": cli.id,
                "metodo_pago": "transferencia",
                "detalles": [{"producto_id": prod.id, "cantidad": 1}],
                "pagos": [{"metodo": "transferencia", "monto": 1000}],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["es_mixto"] is False
        assert len(data["pagos"]) == 1
        assert data["pagos"][0]["metodo"] == "transferencia"
        assert data["metodo_pago"] == "transferencia"

    async def test_create_pedido_pagos_suma_menor(self, client: AsyncClient, admin_headers, session):
        """Suma menor → 422 sin stock ni caja."""
        from app import models
        from tests.assertions import assert_producto_stock
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto
        cat = create_categoria(session, nombre="CatFaltan")
        prov = create_proveedor(session, nombre="ProvFaltan")
        prod = create_producto(session, nombre="ProdFaltan", precio_venta=1000, stock=10,
                               categorias=[cat], proveedor=prov)
        cli = create_cliente(session, nombre="CliFaltanUnico", email="faltan@test.com", dni="20202020")
        session.commit()
        # Setup durable a nivel conexión: el rollback del endpoint ante el 422 solo
        # debe deshacer los cambios del request, no el setup (en producción cada
        # request usa su propia sesión). Se limpia en finally para no fugar filas
        # a otros tests (el :memory: se comparte en la sesión de pytest).
        session.get_bind().commit()
        try:
            resp = await client.post(
                "/pedidos",
                json={
                    "cliente_id": cli.id,
                    "metodo_pago": "efectivo",
                    "detalles": [{"producto_id": prod.id, "cantidad": 1}],
                    "pagos": [{"metodo": "efectivo", "monto": 900}],
                },
                headers=admin_headers,
            )
            assert resp.status_code == 422
            assert "faltan" in resp.json()["detail"].lower()
            assert_producto_stock(session, prod.id, 10)
            assert session.query(models.Pedido).filter(models.Pedido.cliente_id == cli.id).count() == 0
            assert session.query(models.MovimientoCaja).filter(
                models.MovimientoCaja.descripcion.contains("CliFaltanUnico")).count() == 0
        finally:
            prod.categorias = []
            session.delete(prod)
            session.delete(cli)
            session.delete(cat)
            session.delete(prov)
            session.commit()

    async def test_create_pedido_pagos_suma_mayor(self, client: AsyncClient, admin_headers, session):
        """Suma mayor → 422 sin efectos."""
        from app import models
        from tests.assertions import assert_producto_stock
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto
        cat = create_categoria(session, nombre="CatSobran")
        prov = create_proveedor(session, nombre="ProvSobran")
        prod = create_producto(session, nombre="ProdSobran", precio_venta=1000, stock=10,
                               categorias=[cat], proveedor=prov)
        cli = create_cliente(session, nombre="CliSobranUnico", email="sobran@test.com", dni="21212121")
        session.commit()
        # Setup durable (ver test_create_pedido_pagos_suma_menor); limpieza en finally.
        session.get_bind().commit()
        try:
            resp = await client.post(
                "/pedidos",
                json={
                    "cliente_id": cli.id,
                    "metodo_pago": "efectivo",
                    "detalles": [{"producto_id": prod.id, "cantidad": 1}],
                    "pagos": [
                        {"metodo": "efectivo", "monto": 600},
                        {"metodo": "debito", "monto": 500},
                    ],
                },
                headers=admin_headers,
            )
            assert resp.status_code == 422
            assert "sobran" in resp.json()["detail"].lower()
            assert_producto_stock(session, prod.id, 10)
            assert session.query(models.Pedido).filter(models.Pedido.cliente_id == cli.id).count() == 0
            assert session.query(models.MovimientoCaja).filter(
                models.MovimientoCaja.descripcion.contains("CliSobranUnico")).count() == 0
        finally:
            prod.categorias = []
            session.delete(prod)
            session.delete(cli)
            session.delete(cat)
            session.delete(prov)
            session.commit()

    async def test_create_pedido_pagos_monto_cero(self, client: AsyncClient, admin_headers, session):
        """Monto 0 → 422."""
        prod, cli = await self._setup_1000(session)

        resp = await client.post(
            "/pedidos",
            json={
                "cliente_id": cli.id,
                "metodo_pago": "efectivo",
                "detalles": [{"producto_id": prod.id, "cantidad": 1}],
                "pagos": [
                    {"metodo": "efectivo", "monto": 0},
                    {"metodo": "debito", "monto": 1000},
                ],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 422

    async def test_create_pedido_pagos_metodo_invalido(self, client: AsyncClient, admin_headers, session):
        """Método inexistente → 422."""
        prod, cli = await self._setup_1000(session)

        resp = await client.post(
            "/pedidos",
            json={
                "cliente_id": cli.id,
                "metodo_pago": "efectivo",
                "detalles": [{"producto_id": prod.id, "cantidad": 1}],
                "pagos": [{"metodo": "cheque", "monto": 1000}],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 422

    async def test_create_pedido_pagos_lista_vacia(self, client: AsyncClient, admin_headers, session):
        """Lista vacía → 422."""
        prod, cli = await self._setup_1000(session)

        resp = await client.post(
            "/pedidos",
            json={
                "cliente_id": cli.id,
                "metodo_pago": "efectivo",
                "detalles": [{"producto_id": prod.id, "cantidad": 1}],
                "pagos": [],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 422

    async def test_create_pedido_sin_pagos_compat(self, client: AsyncClient, admin_headers, session):
        """Sin campo pagos: flujo único intacto con desglose derivado."""
        prod, cli = await self._setup_1000(session)

        resp = await client.post(
            "/pedidos",
            json={
                "cliente_id": cli.id,
                "metodo_pago": "efectivo",
                "detalles": [{"producto_id": prod.id, "cantidad": 1}],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["metodo_pago"] == "efectivo"
        assert data["es_mixto"] is False
        assert len(data["pagos"]) == 1
        assert data["pagos"][0] == {"id": data["pagos"][0]["id"], "metodo": "efectivo", "monto": 1000.0}

    async def test_cancel_pedido_mixto_crea_salidas(self, client: AsyncClient, admin_headers, session):
        """Cancelar mixta: 2 SALIDAs espejo y stock restituido."""
        from tests.assertions import assert_caja_movement, assert_producto_stock
        prod, cli = await self._setup_1000(session)

        resp = await client.post(
            "/pedidos",
            json={
                "cliente_id": cli.id,
                "metodo_pago": "efectivo",
                "detalles": [{"producto_id": prod.id, "cantidad": 2}],
                "pagos": [
                    {"metodo": "efectivo", "monto": 1200},
                    {"metodo": "debito", "monto": 800},
                ],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        pid = resp.json()["id"]
        assert_producto_stock(session, prod.id, 8)

        cancel = await client.patch(f"/pedidos/{pid}/cancelar", headers=admin_headers)
        assert cancel.status_code == 200
        assert cancel.json()["estado"] == "cancelado"
        assert_producto_stock(session, prod.id, 10)
        assert_caja_movement(session, "SALIDA", "efectivo", f"Anulación venta #{pid}", 1200.0, pedido_id=pid)
        assert_caja_movement(session, "SALIDA", "debito", f"Anulación venta #{pid}", 800.0, pedido_id=pid)

    async def test_get_pedido_legacy_fallback(self, client: AsyncClient, admin_headers, session):
        """Venta sin filas de pago (pre-migración) se lee como pago único."""
        from datetime import datetime
        from app import models
        from tests.factories import create_cliente, create_categoria, create_proveedor, create_producto
        cat = create_categoria(session)
        prov = create_proveedor(session)
        prod = create_producto(session, precio_venta=100, stock=10, categorias=[cat], proveedor=prov)
        cli = create_cliente(session)
        ped = models.Pedido(
            cliente_id=cli.id, fecha=datetime.utcnow(), estado=models.EstadoPedido.pagado,
            metodo_pago=models.MetodoPago.efectivo, moneda="ARS",
            descuento_tipo=models.TipoDescuento.ningun, descuento_valor=0,
            subtotal=100.0, total=100.0, detalles=[],
        )
        session.add(ped)
        session.commit()

        resp = await client.get(f"/pedidos/{ped.id}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["es_mixto"] is False
        assert len(data["pagos"]) == 1
        assert data["pagos"][0]["metodo"] == "efectivo"
        assert data["pagos"][0]["monto"] == 100.0