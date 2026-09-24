"""Seed DEMO UX (datos FICTICIOS, no reales).

Crea un escenario parecido al workflow de la duena sin usar sus datos:
- 2 proveedores ficticios con alias + dias de entrega
- 6 productos DEMO-* con proveedor principal + alternativos
- 1 cliente demo + 1 venta en efectivo con dto 10% + 1 venta con debito

Uso:
    python -m app.seed_demo_ux          # crea solo si no hay productos DEMO-*
    python -m app.seed_demo_ux --reset  # borra SOLO lo DEMO-* y lo recrea

NUNCA toca datos reales: filtra todo por prefijo DEMO- / 'Demo'.
"""
import argparse
import sys
from datetime import datetime

from app.core.database import SessionLocal, Base, engine
from app import models
from app.core.security import hash_password
from app.services.discounts import aplicar_descuento

DEMO_TAG = "DEMO-"


def _limpiar_demo(db):
    prods = db.query(models.Producto).filter(models.Producto.sku.like(f"{DEMO_TAG}%")).all()
    for p in prods:
        db.execute(
            models.producto_proveedor.delete().where(
                models.producto_proveedor.c.producto_id == p.id
            )
        )
        db.query(models.DetallePedido).filter(
            models.DetallePedido.producto_id == p.id
        ).delete()
        db.query(models.MovimientoStock).filter(
            models.MovimientoStock.producto_id == p.id
        ).delete()
        db.delete(p)
    db.flush()
    demo_ped_ids = [
        ped.id
        for ped in (
            db.query(models.Pedido)
            .join(models.Cliente)
            .filter(models.Cliente.nombre.like("Cliente Demo%"))
            .all()
        )
    ]
    for ped in (
        db.query(models.Pedido).filter(models.Pedido.id.in_(demo_ped_ids)).all()
        if demo_ped_ids
        else []
    ):
        db.query(models.MovimientoStock).filter(
            models.MovimientoStock.pedido_id == ped.id
        ).delete()
        db.delete(ped)
    if demo_ped_ids:
        db.query(models.MovimientoCaja).filter(
            models.MovimientoCaja.pedido_id.in_(demo_ped_ids)
        ).delete()
    db.query(models.MovimientoCaja).filter(
        models.MovimientoCaja.descripcion.like("%demo%")
    ).delete()
    db.query(models.Cliente).filter(
        models.Cliente.nombre.like("Cliente Demo%")
    ).delete()
    demo_prov_ids = [
        p.id
        for p in db.query(models.Proveedor).filter(
            models.Proveedor.nombre.like("%Demo%")
        ).all()
    ]
    if demo_prov_ids:
        db.query(models.MovimientoProveedor).filter(
            models.MovimientoProveedor.proveedor_id.in_(demo_prov_ids)
        ).delete()
        demo_comp_ids = [
            c.id
            for c in db.query(models.Compra).filter(
                models.Compra.proveedor_id.in_(demo_prov_ids)
            ).all()
        ]
        if demo_comp_ids:
            db.query(models.MovimientoCaja).filter(
                models.MovimientoCaja.compra_id.in_(demo_comp_ids)
            ).delete()
            db.query(models.MovimientoStock).filter(
                models.MovimientoStock.compra_id.in_(demo_comp_ids)
            ).delete()
            db.query(models.DetalleCompra).filter(
                models.DetalleCompra.compra_id.in_(demo_comp_ids)
            ).delete()
            db.query(models.Compra).filter(
                models.Compra.id.in_(demo_comp_ids)
            ).delete()
    db.query(models.Proveedor).filter(
        models.Proveedor.nombre.like("%Demo%")
    ).delete()
    db.commit()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existe = (
            db.query(models.Producto)
            .filter(models.Producto.sku.like(f"{DEMO_TAG}%"))
            .first()
        )
        if existe and not args.reset:
            print("Demo UX ya existe (usa --reset para recrearla)")
            return 0
        if existe and args.reset:
            _limpiar_demo(db)
            print("Demo UX limpiada (--reset, solo datos DEMO-*)")

        norte = models.Proveedor(
            nombre="Distri Demo Norte",
            contacto="demo.norte@mail.ficticio",
            telefono="000-000",
            alias="demo.norte.mp",
            dias_entrega="todos los dias",
        )
        mayo = models.Proveedor(
            nombre="Mayo Demo",
            contacto="mayo.demo@mail.ficticio",
            telefono="000-001",
            alias="mayo.demo.mp",
            dias_entrega="lun/mie/vie",
        )
        db.add_all([norte, mayo])
        db.flush()

        def add(sku, nombre, precio_costo, precio_venta, stock, principal, alts):
            p = models.Producto(
                sku=f"{DEMO_TAG}{sku}",
                nombre=f"{nombre} (demo)",
                descripcion=f"Producto ficticio {nombre}",
                marca="Demo",
                unidad=models.Unidad.unidad,
                precio_costo=precio_costo,
                precio_venta=precio_venta,
                stock=stock,
                stock_minimo=3,
                activo=True,
                proveedor_id=principal.id,
                proveedores_alt=alts,
            )
            db.add(p)
            db.flush()
            return p

        a = add("BAL-3KG", "Balanceado Demo 3kg", 9000, 12999, 20, norte, [norte, mayo])
        b = add("CAT-7KG", "Gato Demo 7kg", 15000, 21999, 12, mayo, [mayo])
        c = add("CORREA-M", "Correa Demo M", 2500, 5499, 15, norte, [norte])
        add("SNACK-X", "Snack Demo", 800, 1999, 30, norte, [norte, mayo])
        add("SHAMPOO-D", "Shampoo Demo", 2000, 4499, 10, mayo, [mayo, norte])
        add("JUGUETE-D", "Pelota Demo", 700, 1999, 25, norte, [norte])

        cli = models.Cliente(
            nombre="Cliente Demo",
            email="cliente.demo@mail.ficticio",
            telefono="000-100",
            dni="99999999",
            direccion="Calle Ficticia 123",
        )
        db.add(cli)
        db.flush()

        # Venta 1: efectivo con dto 10% (regla EF/TR demo)
        base = round(a.precio_venta * 2, 2)
        sub = aplicar_descuento(base, "ningun", 0)
        total = aplicar_descuento(sub, "porcentaje", 10)
        ped1 = models.Pedido(
            cliente_id=cli.id,
            estado=models.EstadoPedido.pagado,
            metodo_pago=models.MetodoPago.efectivo,
            moneda="ARS",
            descuento_tipo=models.TipoDescuento.porcentaje,
            descuento_valor=10,
            subtotal=sub,
            total=total,
            detalles=[
                models.DetallePedido(
                    producto_id=a.id,
                    cantidad=2,
                    precio_unitario=a.precio_venta,
                    nombre_snapshot=a.nombre,
                    descuento_tipo=models.TipoDescuento.ningun,
                    descuento_valor=0,
                    subtotal_linea=sub,
                )
            ],
        )
        db.add(ped1)
        db.flush()
        ant = a.stock
        a.stock = ant - 2
        db.add(
            models.MovimientoStock(
                producto_id=a.id,
                tipo=models.TipoMovimiento.EGRESO_VENTA,
                cantidad=2,
                stock_anterior=ant,
                stock_nuevo=a.stock,
                pedido_id=ped1.id,
            )
        )

        # Venta 2: debito sin dto (nuevo metodo DB)
        base2 = round(b.precio_venta * 1, 2)
        ped2 = models.Pedido(
            cliente_id=cli.id,
            estado=models.EstadoPedido.pagado,
            metodo_pago=models.MetodoPago.debito,
            moneda="ARS",
            descuento_tipo=models.TipoDescuento.ningun,
            descuento_valor=0,
            subtotal=base2,
            total=base2,
            detalles=[
                models.DetallePedido(
                    producto_id=b.id,
                    cantidad=1,
                    precio_unitario=b.precio_venta,
                    nombre_snapshot=b.nombre,
                    descuento_tipo=models.TipoDescuento.ningun,
                    descuento_valor=0,
                    subtotal_linea=base2,
                )
            ],
        )
        db.add(ped2)
        db.flush()
        ant2 = b.stock
        b.stock = ant2 - 1
        db.add(
            models.MovimientoStock(
                producto_id=b.id,
                tipo=models.TipoMovimiento.EGRESO_VENTA,
                cantidad=1,
                stock_anterior=ant2,
                stock_nuevo=b.stock,
                pedido_id=ped2.id,
            )
        )

        # ---------- Caja ficticia: entradas auto de las ventas + gasto manual ----------
        MP = models.MetodoPago
        db.add_all([
            models.MovimientoCaja(tipo=models.TipoMovCaja.ENTRADA, medio=MP.efectivo,
                                  descripcion=f"Venta #{ped1.id} · {cli.nombre}",
                                  monto=total, pedido_id=ped1.id),
            models.MovimientoCaja(tipo=models.TipoMovCaja.ENTRADA, medio=MP.debito,
                                  descripcion=f"Venta #{ped2.id} · {cli.nombre}",
                                  monto=base2, pedido_id=ped2.id),
            models.MovimientoCaja(tipo=models.TipoMovCaja.SALIDA, medio=MP.efectivo,
                                  descripcion="Cabify demo", monto=6500),
        ])
        db.flush()

        # ---------- Compras ficticias a distribuidoras (pedido -> entrega -> pago) ----------
        def add_compra(prov, nro, lineas, entregada=False, pagada=False, medio=None):
            dets, monto = [], 0.0
            for prod, cant in lineas:
                sub = round(prod.precio_costo * cant, 2)
                monto = round(monto + sub, 2)
                dets.append(models.DetalleCompra(
                    producto_id=prod.id, cantidad=cant,
                    costo_unitario=prod.precio_costo, subtotal=sub))
            comp = models.Compra(
                proveedor_id=prov.id, nro_boleta=nro,
                fecha_entrega=datetime.now() if entregada else None,
                pagado=pagada, medio_pago=medio, monto=monto,
                detalles=dets)
            db.add(comp)
            db.flush()
            if entregada:
                for det in dets:
                    pr = db.get(models.Producto, det.producto_id)
                    ant = pr.stock
                    pr.stock = ant + det.cantidad
                    db.add(models.MovimientoStock(
                        producto_id=pr.id, tipo=models.TipoMovimiento.INGRESO,
                        cantidad=det.cantidad, stock_anterior=ant,
                        stock_nuevo=pr.stock, compra_id=comp.id))
            if pagada:
                db.add(models.MovimientoCaja(
                    tipo=models.TipoMovCaja.SALIDA, medio=medio,
                    descripcion=f"Pago {prov.nombre} {nro}",
                    monto=monto, compra_id=comp.id))
            db.flush()
            return comp

        add_compra(norte, "99001", [(a, 4)], entregada=True, pagada=True, medio=MP.transferencia)
        add_compra(mayo, "77010", [(b, 2)], entregada=False, pagada=False)
        add_compra(norte, "99120", [(c, 5)], entregada=True, pagada=False)

        if not db.query(models.User).filter(models.User.username == "admin").first():
            db.add(
                models.User(
                    username="admin",
                    hashed_password=hash_password("admin123"),
                    rol="admin",
                )
            )
        db.commit()
        print(
            "Seed DEMO UX OK: 2 proveedores ficticios, 6 productos DEMO-*, "
            f"venta #{ped1.id} efectivo -10% total ${total}, "
            f"venta #{ped2.id} debito total ${base2}, "
            "3 compras demo (entregada+pagada, pendiente, entregada impaga)"
        )
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
