"""Factory functions for creating test model instances."""
from datetime import datetime
from sqlalchemy.orm import Session
from app import models

_SKU_COUNTER = 0
_EMAIL_COUNTER = 0
_DNI_COUNTER = 10000000


def _next_sku() -> str:
    global _SKU_COUNTER
    _SKU_COUNTER += 1
    return f"TEST-{_SKU_COUNTER:03d}"


def _next_email() -> str:
    global _EMAIL_COUNTER
    _EMAIL_COUNTER += 1
    return f"test{_EMAIL_COUNTER}@example.com"


def _next_dni() -> str:
    global _DNI_COUNTER
    _DNI_COUNTER += 1
    return str(_DNI_COUNTER)


def create_user(session: Session, rol: str = "vendedor", **overrides) -> models.User:
    username = overrides.pop("username", f"user{_next_sku()}")
    user = models.User(
        username=username,
        hashed_password=overrides.pop("hashed_password", "hashed"),
        rol=rol,
        activo=overrides.pop("activo", True),
    )
    for k, v in overrides.items():
        setattr(user, k, v)
    session.add(user)
    session.flush()
    return user


def create_categoria(session: Session, **overrides) -> models.Categoria:
    nombre = overrides.pop("nombre", f"Categoria {_next_sku()}")
    cat = models.Categoria(nombre=nombre, descripcion=overrides.pop("descripcion", None))
    for k, v in overrides.items():
        setattr(cat, k, v)
    session.add(cat)
    session.flush()
    return cat


def create_producto(session: Session, **overrides) -> models.Producto:
    sku = overrides.pop("sku", _next_sku())
    nombre = overrides.pop("nombre", f"Producto {sku}")
    cats = overrides.pop("categorias", [])
    proveedor = overrides.pop("proveedor", None)
    proveedores_alt = overrides.pop("proveedores_alt", [])

    prod = models.Producto(
        sku=sku,
        nombre=nombre,
        descripcion=overrides.pop("descripcion", None),
        marca=overrides.pop("marca", None),
        unidad=overrides.pop("unidad", models.Unidad.unidad),
        precio_costo=overrides.pop("precio_costo", 100.0),
        precio_venta=overrides.pop("precio_venta", 200.0),
        stock=overrides.pop("stock", 10),
        stock_minimo=overrides.pop("stock_minimo", 5),
        imagen_url=overrides.pop("imagen_url", None),
        activo=overrides.pop("activo", True),
        proveedor=proveedor,
    )
    if cats:
        prod.categorias = cats
    if proveedores_alt:
        prod.proveedores_alt = proveedores_alt

    for k, v in overrides.items():
        setattr(prod, k, v)
    session.add(prod)
    session.flush()
    return prod


def create_cliente(session: Session, **overrides) -> models.Cliente:
    cli = models.Cliente(
        nombre=overrides.pop("nombre", "Cliente Test"),
        email=overrides.pop("email", _next_email()),
        telefono=overrides.pop("telefono", None),
        dni=overrides.pop("dni", _next_dni()),
        direccion=overrides.pop("direccion", None),
    )
    for k, v in overrides.items():
        setattr(cli, k, v)
    session.add(cli)
    session.flush()
    return cli


def create_proveedor(session: Session, **overrides) -> models.Proveedor:
    prov = models.Proveedor(
        nombre=overrides.pop("nombre", f"Proveedor {_next_sku()}"),
        contacto=overrides.pop("contacto", None),
        telefono=overrides.pop("telefono", None),
        alias=overrides.pop("alias", None),
        dias_entrega=overrides.pop("dias_entrega", None),
    )
    for k, v in overrides.items():
        setattr(prov, k, v)
    session.add(prov)
    session.flush()
    return prov


def create_pedido(session: Session, cliente: models.Cliente, detalles: list, metodo_pago: models.MetodoPago = models.MetodoPago.efectivo, **overrides) -> models.Pedido:
    from app.services.discounts import aplicar_descuento

    subtotal = 0.0
    detalles_db = []
    movimientos = []

    for det in detalles:
        producto = det["producto"]
        cantidad = det["cantidad"]
        descuento_tipo = det.get("descuento_tipo", models.TipoDescuento.ningun)
        descuento_valor = det.get("descuento_valor", 0)

        base = round(producto.precio_venta * cantidad, 2)
        sub_linea = aplicar_descuento(base, descuento_tipo.value, descuento_valor)
        subtotal = round(subtotal + sub_linea, 2)

        ant = producto.stock
        producto.stock = ant - cantidad
        movimientos.append(models.MovimientoStock(
            producto_id=producto.id,
            tipo=models.TipoMovimiento.EGRESO_VENTA,
            cantidad=cantidad,
            stock_anterior=ant,
            stock_nuevo=producto.stock,
        ))

        detalles_db.append(models.DetallePedido(
            producto_id=producto.id,
            cantidad=cantidad,
            precio_unitario=producto.precio_venta,
            nombre_snapshot=producto.nombre,
            descuento_tipo=descuento_tipo,
            descuento_valor=descuento_valor,
            subtotal_linea=sub_linea,
        ))

    descuento_tipo = overrides.pop("descuento_tipo", models.TipoDescuento.ningun)
    descuento_valor = overrides.pop("descuento_valor", 0)
    total = aplicar_descuento(subtotal, descuento_tipo.value, descuento_valor)

    ped = models.Pedido(
        cliente_id=cliente.id,
        fecha=overrides.pop("fecha", datetime.utcnow()),
        estado=overrides.pop("estado", models.EstadoPedido.pagado),
        metodo_pago=metodo_pago,
        moneda="ARS",
        descuento_tipo=descuento_tipo,
        descuento_valor=descuento_valor,
        subtotal=subtotal,
        total=total,
        detalles=detalles_db,
        pagos=[models.PagoPedido(metodo=metodo_pago, monto=total)],
    )
    session.add(ped)
    session.flush()

    for m in movimientos:
        m.pedido_id = ped.id
        session.add(m)

    session.add(models.MovimientoCaja(
        tipo=models.TipoMovCaja.ENTRADA,
        medio=metodo_pago,
        descripcion=f"Venta #{ped.id} · {cliente.nombre}",
        monto=total,
        pedido_id=ped.id,
    ))

    session.flush()
    return ped


def create_compra(session: Session, proveedor: models.Proveedor, detalles: list, pagado: bool = False, medio_pago: models.MetodoPago | None = None, **overrides) -> models.Compra:
    detalles_db = []
    monto = 0.0

    for det in detalles:
        producto = det["producto"]
        cantidad = det["cantidad"]
        costo_unitario = det.get("costo_unitario", producto.precio_costo or 0)
        sub = round(costo_unitario * cantidad, 2)
        monto = round(monto + sub, 2)
        detalles_db.append(models.DetalleCompra(
            producto_id=producto.id,
            cantidad=cantidad,
            costo_unitario=costo_unitario,
            subtotal=sub,
        ))

    if not detalles_db:
        raise ValueError("La compra necesita al menos una línea")

    comp = models.Compra(
        proveedor_id=proveedor.id,
        nro_boleta=overrides.pop("nro_boleta", f"BOL-{_next_sku()}"),
        fecha_pedido=overrides.pop("fecha_pedido", datetime.utcnow()),
        pagado=pagado,
        medio_pago=medio_pago,
        monto=monto,
        detalles=detalles_db,
    )
    session.add(comp)
    session.flush()

    if pagado and medio_pago:
        session.add(models.MovimientoCaja(
            tipo=models.TipoMovCaja.SALIDA,
            medio=medio_pago,
            descripcion=f"Pago {proveedor.nombre} {comp.nro_boleta}",
            monto=monto,
            fecha=comp.fecha_pedido,
            compra_id=comp.id,
        ))

    session.flush()
    return comp


def create_movimiento_stock(session: Session, producto: models.Producto, tipo: models.TipoMovimiento, cantidad: int, **overrides) -> models.MovimientoStock:
    ant = producto.stock
    if tipo == models.TipoMovimiento.INGRESO:
        nuevo = ant + cantidad
    elif tipo == models.TipoMovimiento.EGRESO_VENTA:
        nuevo = ant - cantidad
    elif tipo == models.TipoMovimiento.DEVOLUCION_CANCEL:
        nuevo = ant + cantidad
    else:
        nuevo = ant

    mov = models.MovimientoStock(
        producto_id=producto.id,
        tipo=tipo,
        cantidad=cantidad,
        stock_anterior=ant,
        stock_nuevo=nuevo,
        pedido_id=overrides.pop("pedido_id", None),
        compra_id=overrides.pop("compra_id", None),
    )
    session.add(mov)
    session.flush()
    return mov


def create_movimiento_caja(session: Session, tipo: models.TipoMovCaja, medio: models.MetodoPago, descripcion: str, monto: float, **overrides) -> models.MovimientoCaja:
    mov = models.MovimientoCaja(
        tipo=tipo,
        medio=medio,
        descripcion=descripcion,
        monto=monto,
        pedido_id=overrides.pop("pedido_id", None),
        compra_id=overrides.pop("compra_id", None),
    )
    session.add(mov)
    session.flush()
    return mov


def create_movimiento_proveedor(session: Session, proveedor: models.Proveedor, tipo: models.TipoMovProveedor, nro: str, monto: float, **overrides) -> models.MovimientoProveedor:
    mov = models.MovimientoProveedor(
        proveedor_id=proveedor.id,
        tipo=tipo,
        nro=nro,
        monto=monto,
        fecha=overrides.pop("fecha", datetime.utcnow()),
    )
    session.add(mov)
    session.flush()

    if tipo in (models.TipoMovProveedor.PAGO_EFECTIVO_002, models.TipoMovProveedor.PAGO_TRANSFER_003):
        medio = models.MetodoPago.efectivo if tipo == models.TipoMovProveedor.PAGO_EFECTIVO_002 else models.MetodoPago.transferencia
        session.add(models.MovimientoCaja(
            tipo=models.TipoMovCaja.SALIDA,
            medio=medio,
            descripcion=f"Pago {proveedor.nombre} {nro}",
            monto=monto,
            fecha=mov.fecha,
        ))
        session.flush()

    return mov


def seed_minimal_catalog(session: Session) -> dict:
    """Creates 1 categoria, 1 proveedor, 3 productos, 1 cliente for quick test setup."""
    cat = create_categoria(session, nombre="Alimentos")
    prov = create_proveedor(session, nombre="Distribuidora Test", alias="DT")
    prod1 = create_producto(session, nombre="Alimento Perro", precio_venta=1500, stock=10, categorias=[cat], proveedor=prov)
    prod2 = create_producto(session, nombre="Alimento Gato", precio_venta=1200, stock=5, categorias=[cat], proveedor=prov)
    prod3 = create_producto(session, nombre="Juguete", precio_venta=500, stock=20, categorias=[cat], proveedor=prov)
    cli = create_cliente(session, nombre="Cliente Test", email=_next_email(), dni=_next_dni())
    session.flush()
    return {"categoria": cat, "proveedor": prov, "productos": [prod1, prod2, prod3], "cliente": cli}