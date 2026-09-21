"""Seed demo petshop — dataset completo para demo de 1 semana.

Uso:
    python -m app.seed            # crea solo si la DB está vacía
    python -m app.seed --reset    # borra todo y recarga la demo completa

En Render se ejecuta sin --reset vía start.sh con SEED_ON_START=true,
así el primer deploy carga la demo y los siguientes conservan los datos.
"""
import argparse
import sys
from datetime import datetime, timedelta

from app.core.database import SessionLocal, Base, engine
from app import models
from app.core.security import hash_password
from app.services.discounts import aplicar_descuento


def reset_db(db):
    # Orden inverso a dependencias FK
    db.query(models.MovimientoStock).delete()
    db.query(models.DetallePedido).delete()
    db.query(models.Pedido).delete()
    db.execute(models.producto_categoria.delete())
    db.query(models.Producto).delete()
    db.query(models.Categoria).delete()
    db.query(models.Cliente).delete()
    db.query(models.Proveedor).delete()
    db.query(models.User).delete()
    db.commit()


def crear_pedido(db, fecha, cliente, metodo, lineas, dto_tipo="ningun", dto_valor=0,
                 estado="pagado"):
    """lineas: [(producto, cantidad, dto_tipo, dto_valor)]. Descuenta stock y genera movimientos."""
    detalles, movs, subtotal = [], [], 0.0
    for prod, cant, lt, lv in lineas:
        if prod.stock < cant:
            raise ValueError(f"Sin stock para seed: {prod.nombre} pide {cant}, hay {prod.stock}")
        base = round(prod.precio_venta * cant, 2)
        sub_linea = aplicar_descuento(base, lt, lv)
        subtotal = round(subtotal + sub_linea, 2)
        ant = prod.stock
        prod.stock = ant - cant
        movs.append(models.MovimientoStock(
            producto_id=prod.id, tipo=models.TipoMovimiento.EGRESO_VENTA,
            cantidad=cant, stock_anterior=ant, stock_nuevo=prod.stock, fecha=fecha))
        detalles.append(models.DetallePedido(
            producto_id=prod.id, cantidad=cant, precio_unitario=prod.precio_venta,
            nombre_snapshot=prod.nombre, descuento_tipo=lt, descuento_valor=lv,
            subtotal_linea=sub_linea))
    total = aplicar_descuento(subtotal, dto_tipo, dto_valor)
    ped = models.Pedido(
        cliente_id=cliente.id, fecha=fecha,
        estado=models.EstadoPedido.cancelado if estado == "cancelado" else models.EstadoPedido.pagado,
        metodo_pago=metodo, moneda="ARS",
        descuento_tipo=dto_tipo, descuento_valor=dto_valor,
        subtotal=subtotal, total=total, detalles=detalles)
    db.add(ped)
    db.flush()
    for m in movs:
        m.pedido_id = ped.id
        db.add(m)
    db.flush()
    if estado == "cancelado":
        # Devolver stock como hace PATCH /pedidos/{id}/cancelar
        for det in detalles:
            prod = db.get(models.Producto, det.producto_id)
            ant = prod.stock
            prod.stock = ant + det.cantidad
            db.add(models.MovimientoStock(
                producto_id=prod.id, tipo=models.TipoMovimiento.DEVOLUCION_CANCEL,
                cantidad=det.cantidad, stock_anterior=ant, stock_nuevo=prod.stock,
                pedido_id=ped.id, fecha=fecha + timedelta(hours=1)))
    return ped


def ingreso(db, fecha, prod, cant):
    ant = prod.stock
    prod.stock = ant + cant
    db.add(models.MovimientoStock(
        producto_id=prod.id, tipo=models.TipoMovimiento.INGRESO,
        cantidad=cant, stock_anterior=ant, stock_nuevo=prod.stock, fecha=fecha))
    db.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="borra todo y recarga la demo")
    args = ap.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(models.Categoria).first():
            if not args.reset:
                print("Seed ya existente (usa --reset para recargar la demo completa)")
                return
            reset_db(db)
            print("DB limpiada (--reset)")

        hoy = datetime.now().replace(microsecond=0)
        manana = lambda h: hoy.replace(hour=h, minute=10)  # noqa: E731 ventas repartidas hoy

        # ---------- Categorías ----------
        cats = {}
        for nombre, desc in [
            ("Alimentos", "Comida para mascotas"),
            ("Snacks", "Premios y galletitas"),
            ("Higiene", "Cuidado e higiene"),
            ("Juguetes", "Juegos y entretenimiento"),
            ("Accesorios", "Correas, collares y platos"),
            ("Farmacia", "Antiparasitarios y vitaminas"),
            ("Cuchas y Transporte", "Descanso y traslado"),
        ]:
            c = models.Categoria(nombre=nombre, descripcion=desc)
            db.add(c)
            cats[nombre] = c
        db.flush()

        # ---------- Productos (sku, nombre, marca, unidad, costo, venta, stock, min, cats, activo) ----------
        P = {}

        def add_prod(sku, nombre, marca, unidad, costo, venta, stock, smin, catnames, desc="", activo=True):
            p = models.Producto(
                sku=sku, nombre=nombre, descripcion=desc or nombre, marca=marca,
                unidad=unidad, precio_costo=costo, precio_venta=venta,
                stock=stock, stock_minimo=smin, activo=activo,
                categorias=[cats[n] for n in catnames])
            db.add(p)
            db.flush()
            P[sku] = p
            return p

        U = models.Unidad
        add_prod("RC-MINI-3KG", "Royal Canin Mini Adulto 3kg", "Royal Canin", U.kg, 18000, 24999, 30, 10, ["Alimentos"])
        add_prod("RC-MINI-10KG", "Royal Canin Mini Adulto 10kg", "Royal Canin", U.kg, 52000, 69999, 14, 10, ["Alimentos"])
        add_prod("PROPLAN-AD-15KG", "Pro Plan Adulto 15kg", "Purina", U.kg, 48000, 64999, 20, 8, ["Alimentos"])
        add_prod("WHISKAS-GATO-10KG", "Whiskas Pescado 10kg", "Whiskas", U.kg, 32000, 42999, 18, 8, ["Alimentos"])
        add_prod("SNACK-HUESO-500G", "Huesitos snack 500g", "PetFun", U.unidad, 2500, 4999, 40, 10, ["Snacks"])
        add_prod("GALLETA-PERRO-1KG", "Galletitas huesito 1kg", "Animall", U.kg, 3000, 5999, 35, 10, ["Snacks"])
        add_prod("SHAMPOO-PULGAS-500ML", "Shampoo antipulgas 500ml", "Osmac", U.unidad, 4000, 7999, 22, 6, ["Higiene"])
        add_prod("PIEDRA-GATO-4KG", "Piedras sanitarias 4kg", "Absorsol", U.kg, 3500, 6999, 25, 10, ["Higiene"])
        add_prod("TOALLITAS-50U", "Toallitas húmedas x50", "PetCare", U.pack, 2000, 3999, 30, 10, ["Higiene"])
        add_prod("PELOTA-01", "Pelota resistente", "PetFun", U.unidad, 1500, 3499, 50, 10, ["Juguetes"])
        add_prod("SOGA-DENTAL", "Soga dental", "PetFun", U.unidad, 1800, 3999, 28, 8, ["Juguetes"])
        add_prod("RATON-CATNIP", "Ratón con catnip", "CatJoy", U.unidad, 1200, 2799, 33, 10, ["Juguetes"])
        add_prod("CORREA-RETR-5M", "Correa retráctil 5m", "Trixie", U.unidad, 8000, 14999, 15, 5, ["Accesorios"])
        add_prod("COLLAR-NYLON-M", "Collar nylon talle M", "Trixie", U.unidad, 2500, 5499, 20, 5, ["Accesorios"])
        add_prod("PLATO-ACERO", "Plato acero inoxidable", "Ferplast", U.unidad, 3000, 6499, 18, 5, ["Accesorios"])
        add_prod("CORREA-SUELTA", "Correa suelta (demo Sin categoría)", "Genérica", U.unidad, 1500, 2999, 12, 5, [])
        add_prod("ANTIPAR-10KG", "Antiparasitario 10kg", "Basken", U.unidad, 5000, 9999, 16, 6, ["Farmacia"])
        add_prod("VIT-60C", "Vitaminas x60 comp", "Lab Vet", U.unidad, 6000, 11999, 4, 5, ["Farmacia"])
        add_prod("CUCHA-XL", "Cucha plástica XL", "Ferplast", U.unidad, 25000, 44999, 0, 3, ["Cuchas y Transporte"])
        add_prod("TRANSP-M", "Transportadora mediana", "Ferplast", U.unidad, 22000, 39999, 7, 3, ["Cuchas y Transporte"])
        add_prod("MOCHILA-CAT", "Mochila transportadora gato (inactiva demo)", "CatJoy", U.unidad, 18000, 32999, 9, 3,
                 ["Cuchas y Transporte"], activo=False)

        # ---------- Clientes ----------
        CLI = {}
        for nombre, email, tel, dni, direc in [
            ("Martina López", "martina.lopez@mail.com", "351-2345678", "30123456", "Av Colón 1234, Córdoba"),
            ("Diego Ramírez", "diego.ramirez@mail.com", "351-8765432", "31234567", "Belgrano 567, Córdoba"),
            ("Sofía Fernández", "sofia.fernandez@mail.com", "351-4567890", "32345678", "San Martín 890, Villa María"),
            ("Camila Torres", "camila.torres@mail.com", "351-3456789", "33456789", "Rivadavia 234, Río Cuarto"),
            ("Lucas García", "lucas.garcia@mail.com", "351-5678901", "34567890", "Mitre 678, Córdoba"),
            ("Valentina Sosa", "valentina.sosa@mail.com", "351-6789012", "35678901", "Alberdi 345, Alta Gracia"),
            ("Pedro Gómez", "pedro.gomez@mail.com", "351-7890123", "36789012", "Sarmiento 789, Jesús María"),
            ("Lucía Herrera", "lucia.herrera@mail.com", "351-8901234", "37890123", "Laprida 456, Córdoba"),
        ]:
            c = models.Cliente(nombre=nombre, email=email, telefono=tel, dni=dni, direccion=direc)
            db.add(c)
            db.flush()
            CLI[email] = c

        # ---------- Proveedores ----------
        for nombre, contacto, tel in [
            ("Distribuidora Sur", "ventas@disur.com", "011-4567-8900"),
            ("PetFood Mayorista", "pedidos@petfoodmayorista.com", "011-5678-9012"),
            ("Higiene & Co", "contacto@higieneandco.com", "0351-678-9012"),
            ("PetFun Mayorista", "mayorista@petfun.com", "011-7890-1234"),
        ]:
            db.add(models.Proveedor(nombre=nombre, contacto=contacto, telefono=tel))
        db.flush()

        # ---------- Usuarios ----------
        db.add(models.User(username="admin", hashed_password=hash_password("admin123"), rol="admin"))
        db.add(models.User(username="vendedora", hashed_password=hash_password("demo1234"), rol="vendedor"))
        db.flush()

        # ---------- Ingresos de mercadería hoy (para Historial) ----------
        ingreso(db, manana(9), P["PROPLAN-AD-15KG"], 15)
        ingreso(db, manana(9), P["TOALLITAS-50U"], 20)
        ingreso(db, manana(9), P["COLLAR-NYLON-M"], 10)

        # ---------- Pedidos pagados hoy ----------
        MP = models.MetodoPago
        C = CLI
        crear_pedido(db, manana(10), C["martina.lopez@mail.com"], MP.efectivo,
                     [(P["RC-MINI-3KG"], 2, "ningun", 0), (P["PELOTA-01"], 1, "ningun", 0)])
        crear_pedido(db, manana(11), C["diego.ramirez@mail.com"], MP.tarjeta,
                     [(P["PROPLAN-AD-15KG"], 1, "porcentaje", 10), (P["SHAMPOO-PULGAS-500ML"], 2, "ningun", 0)],
                     dto_tipo="porcentaje", dto_valor=5)
        crear_pedido(db, manana(11), C["sofia.fernandez@mail.com"], MP.transferencia,
                     [(P["WHISKAS-GATO-10KG"], 1, "ningun", 0), (P["PIEDRA-GATO-4KG"], 2, "ningun", 0)])
        crear_pedido(db, manana(12), C["martina.lopez@mail.com"], MP.mercadopago,
                     [(P["SOGA-DENTAL"], 1, "ningun", 0), (P["RATON-CATNIP"], 2, "ningun", 0),
                      (P["GALLETA-PERRO-1KG"], 1, "ningun", 0)],
                     dto_tipo="monto_fijo", dto_valor=2000)
        crear_pedido(db, manana(13), C["camila.torres@mail.com"], MP.efectivo,
                     [(P["CORREA-RETR-5M"], 1, "ningun", 0), (P["COLLAR-NYLON-M"], 1, "ningun", 0),
                      (P["CORREA-SUELTA"], 1, "ningun", 0)])
        crear_pedido(db, manana(14), C["lucas.garcia@mail.com"], MP.tarjeta,
                     [(P["SNACK-HUESO-500G"], 3, "monto_fijo", 500)])
        crear_pedido(db, manana(15), C["diego.ramirez@mail.com"], MP.efectivo,
                     [(P["ANTIPAR-10KG"], 1, "ningun", 0), (P["VIT-60C"], 1, "ningun", 0)])
        crear_pedido(db, manana(16), C["valentina.sosa@mail.com"], MP.transferencia,
                     [(P["RC-MINI-10KG"], 6, "ningun", 0)])  # deja stock 8/10 → stock bajo
        crear_pedido(db, manana(17), C["pedro.gomez@mail.com"], MP.mercadopago,
                     [(P["TRANSP-M"], 1, "ningun", 0), (P["PLATO-ACERO"], 1, "ningun", 0)])
        crear_pedido(db, manana(18), C["lucia.herrera@mail.com"], MP.efectivo,
                     [(P["TOALLITAS-50U"], 2, "ningun", 0), (P["SHAMPOO-PULGAS-500ML"], 1, "ningun", 0)])

        # ---------- Pedidos cancelados hoy (muestran devolución) ----------
        crear_pedido(db, manana(12), C["sofia.fernandez@mail.com"], MP.tarjeta,
                     [(P["PROPLAN-AD-15KG"], 2, "ningun", 0), (P["SNACK-HUESO-500G"], 2, "ningun", 0)],
                     estado="cancelado")
        crear_pedido(db, manana(13), C["lucas.garcia@mail.com"], MP.efectivo,
                     [(P["PELOTA-01"], 4, "ningun", 0)], estado="cancelado")

        db.commit()
        nprods = db.query(models.Producto).count()
        npeds = db.query(models.Pedido).count()
        print(f"Seed OK demo completa: 7 categorias, {nprods} productos, 8 clientes, "
              f"4 proveedores, {npeds} pedidos hoy, admin/admin123 + vendedora/demo1234")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
