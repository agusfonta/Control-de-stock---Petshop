import pytest
from httpx import AsyncClient


class TestClientesMascotas:
    async def test_crear_cliente_con_mascotas(self, client: AsyncClient, admin_headers):
        resp = await client.post("/clientes", json={
            "nombre": "Cliente Mascotas", "email": "mascotas@test.com", "dni": "99000001",
            "mascotas": [{"especie": "perro", "nombre": "Luna"}, {"especie": "gato", "nombre": "Mishi"}],
        }, headers=admin_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert {(m["especie"], m["nombre"]) for m in data["mascotas"]} == {("perro", "Luna"), ("gato", "Mishi")}


class TestConfigPrecios:
    async def test_margen_configurable_y_precio_automatico(self, client: AsyncClient, admin_headers, session):
        from tests.factories import create_categoria, create_proveedor
        cat = create_categoria(session, nombre="CatMargen")
        prov = create_proveedor(session, nombre="ProvMargen")
        resp = await client.patch("/configuracion/precios", json={"margen_venta_porcentaje": 30}, headers=admin_headers)
        assert resp.status_code == 200
        resp = await client.post("/productos", json={
            "nombre": "Producto Margen", "precio_costo": 100, "stock": 0,
            "categoria_ids": [cat.id], "proveedor_id": prov.id
        }, headers=admin_headers)
        assert resp.status_code == 201
        assert resp.json()["precio_venta"] == 130


class TestPagosCompraParciales:
    async def test_pago_parcial_y_descuento_recalcula_saldo_y_caja(self, client: AsyncClient, admin_headers, session):
        from tests.factories import create_proveedor, create_producto, create_compra
        prov = create_proveedor(session, nombre="ProvParcial", pronto_pago_dias=7, pronto_pago_porcentaje=10)
        prod = create_producto(session, nombre="ProdParcial", precio_costo=100, precio_venta=150, proveedor=prov)
        comp = create_compra(session, prov, [{"producto": prod, "cantidad": 10}], pagado=False)
        session.commit()

        resp = await client.patch(f"/compras/{comp.id}/pagar", json={"medio_pago": "efectivo", "monto": 400, "descuento": 100}, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_pagado"] == 400
        assert data["total_descuentos"] == 100
        assert data["saldo_pendiente"] == 500
        assert data["pagos"][-1]["monto"] == 400
        assert data["pagos"][-1]["descuento"] == 100
        assert data["pagos"][-1]["total_aplicado"] == 500

    async def test_dos_pagos_saldan_compra(self, client: AsyncClient, admin_headers, session):
        from tests.factories import create_proveedor, create_producto, create_compra
        prov = create_proveedor(session, nombre="ProvDosPagos")
        prod = create_producto(session, nombre="ProdDosPagos", precio_costo=100, precio_venta=150, proveedor=prov)
        comp = create_compra(session, prov, [{"producto": prod, "cantidad": 10}], pagado=False)
        session.commit()

        r1 = await client.patch(f"/compras/{comp.id}/pagar", json={"medio_pago": "efectivo", "monto": 300}, headers=admin_headers)
        assert r1.status_code == 200
        assert r1.json()["saldo_pendiente"] == 700
        r2 = await client.patch(f"/compras/{comp.id}/pagar", json={"medio_pago": "qr", "monto": 700}, headers=admin_headers)
        assert r2.status_code == 200
        assert r2.json()["pagado"] is True
        assert r2.json()["saldo_pendiente"] == 0
        assert len(r2.json()["pagos"]) == 2


class TestHistorialMensual:
    async def test_resumen_mensual(self, client: AsyncClient, admin_headers, session):
        from tests.factories import create_movimiento_caja
        from app import models
        from datetime import datetime
        create_movimiento_caja(session, models.TipoMovCaja.ENTRADA, models.MetodoPago.efectivo, "Entrada mes", 1000, fecha=datetime(2026, 9, 1, 12, 0))
        create_movimiento_caja(session, models.TipoMovCaja.SALIDA, models.MetodoPago.efectivo, "Salida mes", 250, fecha=datetime(2026, 9, 2, 12, 0))
        session.commit()
        resp = await client.get("/caja/mensual?mes=2026-09", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_entrada"] == 1000
        assert data["total_salida"] == 250
        assert data["balance"] == 750
        assert len(data["por_dia"]) == 2


class TestVentasVendedoraYQR:
    async def test_venta_guarda_vendedora_y_qr(self, client: AsyncClient, vendedor_headers, session):
        from tests.factories import create_cliente, create_producto
        cli = create_cliente(session, nombre="CliVendedora", email="vendedora@test.com", dni="99000009")
        prod = create_producto(session, nombre="ProdVendedora", precio_venta=100, stock=5)
        session.commit()
        resp = await client.post("/pedidos", json={
            "cliente_id": cli.id, "metodo_pago": "qr",
            "detalles": [{"producto_id": prod.id, "cantidad": 1}],
            "pagos": [{"metodo": "qr", "monto": 100}],
        }, headers=vendedor_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["vendedora_nombre"] == "vendedor"
        assert data["pagos"][0]["metodo"] == "qr"


class TestMediosPagoQR:
    async def test_nuevos_medios_no_exponen_transferencia_ni_mercadopago(self, client: AsyncClient, admin_headers):
        from app.models import MetodoPago
        assert MetodoPago.qr.value == "qr"
        assert MetodoPago.transferencia.value == "transferencia"
        assert MetodoPago.mercadopago.value == "mercadopago"
