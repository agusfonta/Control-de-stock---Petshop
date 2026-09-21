import csv, io
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app import models, schemas
from app.deps import require_roles

router = APIRouter(prefix="/productos", tags=["productos"])
leer = Depends(require_roles("admin", "vendedor"))
admin = Depends(require_roles("admin"))

def _out(p: models.Producto) -> schemas.ProductoOut:
    o = schemas.ProductoOut.model_validate(p)
    o.stock_bajo = (p.stock <= (p.stock_minimo or 0))
    return o

def _norm_sku(sku: str | None) -> str | None:
    s = (sku or "").strip()
    return s or None

@router.post("", response_model=schemas.ProductoOut, status_code=201, dependencies=[leer])
def crear(d: schemas.ProductoCreate, db: Session = Depends(get_db)):
    sku = _norm_sku(d.sku)
    if sku and db.query(models.Producto).filter(models.Producto.sku == sku).first():
        raise HTTPException(400, "SKU ya existe")
    cats = db.query(models.Categoria).filter(models.Categoria.id.in_(d.categoria_ids)).all() if d.categoria_ids else []
    if len(cats) != len(set(d.categoria_ids)):
        raise HTTPException(400, "Una o mas categorias no existen.")
    p = models.Producto(
        sku=sku, nombre=d.nombre, descripcion=d.descripcion, marca=d.marca,
        unidad=d.unidad, precio_costo=d.precio_costo, precio_venta=d.precio_venta,
        stock=d.stock, stock_minimo=d.stock_minimo, imagen_url=d.imagen_url,
        activo=d.activo, categorias=cats,
    )
    db.add(p); db.commit(); db.refresh(p)
    return _out(p)

@router.get("", response_model=list[schemas.ProductoOut], dependencies=[leer])
def listar(
    db: Session = Depends(get_db),
    categoria: int | None = None,
    search: str | None = None,
    stock_bajo: bool = False,
    solo_activos: bool = False,
):
    q = db.query(models.Producto).options(joinedload(models.Producto.categorias))
    if categoria:
        q = q.join(models.Producto.categorias).filter(models.Categoria.id == categoria)
    if search:
        like = f"%{search}%"
        q = q.filter((models.Producto.nombre.ilike(like)) | (models.Producto.marca.ilike(like)))
    if solo_activos:
        q = q.filter(models.Producto.activo == True)  # noqa
    items = q.order_by(models.Producto.nombre).all()
    out = [_out(p) for p in items]
    if stock_bajo:
        out = [o for o in out if o.stock_bajo]
    return out

@router.get("/{pid}", response_model=schemas.ProductoOut, dependencies=[leer])
def obtener(pid: int, db: Session = Depends(get_db)):
    p = db.query(models.Producto).options(joinedload(models.Producto.categorias)).filter(models.Producto.id == pid).first()
    if not p: raise HTTPException(404, "Producto no encontrado")
    return _out(p)

@router.patch("/{pid}", response_model=schemas.ProductoOut, dependencies=[leer])
def actualizar(pid: int, d: schemas.ProductoUpdate, db: Session = Depends(get_db)):
    p = db.get(models.Producto, pid)
    if not p: raise HTTPException(404, "Producto no encontrado")
    data = d.model_dump(exclude_unset=True, exclude={"categoria_ids", "sku"})
    for k, v in data.items():
        setattr(p, k, v)
    if "sku" in d.model_dump(exclude_unset=True):
        sku = _norm_sku(d.sku)
        if sku and db.query(models.Producto).filter(models.Producto.sku == sku, models.Producto.id != pid).first():
            raise HTTPException(400, "SKU ya existe en otro producto")
        p.sku = sku
    if d.categoria_ids is not None:
        cats = db.query(models.Categoria).filter(models.Categoria.id.in_(d.categoria_ids)).all() if d.categoria_ids else []
        if len(cats) != len(set(d.categoria_ids)):
            raise HTTPException(400, "Categoria invalida")
        p.categorias = cats
    db.commit(); db.refresh(p)
    return _out(p)

@router.delete("/{pid}", status_code=204, dependencies=[admin])
def eliminar(pid: int, db: Session = Depends(get_db)):
    p = db.get(models.Producto, pid)
    if not p: raise HTTPException(404, "Producto no encontrado")
    if db.query(models.DetallePedido).filter(models.DetallePedido.producto_id == pid).first():
        raise HTTPException(400, "No se puede eliminar: el producto tiene ventas asociadas. Desactívalo en su lugar.")
    db.delete(p); db.commit()
    return None

@router.post("/import-csv", response_model=dict, dependencies=[leer])
def importar_csv(file: UploadFile, db: Session = Depends(get_db)):
    """Plantilla: sku,nombre,descripcion,marca,unidad,precio_costo,precio_venta,stock,stock_minimo,categorias(|Separadas),imagen_url.
    Las categorias que no existan se crean automáticamente."""
    try:
        raw = file.file.read().decode("utf-8-sig")
    except Exception:
        raise HTTPException(400, "Archivo ilegible: debe ser CSV en UTF-8")
    reader = csv.DictReader(io.StringIO(raw))
    if not reader.fieldnames or "nombre" not in reader.fieldnames or "precio_venta" not in reader.fieldnames:
        raise HTTPException(400, "CSV inválido: columnas mínimas 'nombre' y 'precio_venta'")
    creados, cat_creadas = 0, set()
    valid_unidades = {"unidad", "kg", "lt", "pack"}
    for i, row in enumerate(reader, start=2):
        try:
            nombre = (row.get("nombre") or "").strip()
            if len(nombre) < 2:
                raise ValueError("nombre requerido (mín 2 caracteres)")
            precio_venta = float(row.get("precio_venta") or "nan")
            if not (precio_venta > 0):
                raise ValueError("precio_venta debe ser > 0")
            precio_costo = float(row.get("precio_costo") or 0)
            if precio_costo < 0:
                raise ValueError("precio_costo debe ser >= 0")
            stock = int(row.get("stock") or 0)
            stock_min = int(row.get("stock_minimo") or 10)
            if stock < 0 or stock_min < 0:
                raise ValueError("stock/stock_minimo deben ser >= 0")
            unidad = (row.get("unidad") or "unidad").strip() or "unidad"
            if unidad not in valid_unidades:
                raise ValueError(f"unidad inválida (usar {sorted(valid_unidades)})")
            sku = _norm_sku(row.get("sku"))
            if sku and db.query(models.Producto).filter(models.Producto.sku == sku).first():
                raise ValueError(f"SKU '{sku}' ya existe")
            nombres = [x.strip() for x in (row.get("categorias") or "").split("|") if x.strip()]
            cats = []
            for n in nombres:
                c = db.query(models.Categoria).filter(models.Categoria.nombre == n).first()
                if not c:
                    c = models.Categoria(nombre=n); db.add(c); db.flush(); cat_creadas.add(n)
                cats.append(c)
            img = (row.get("imagen_url") or "").strip() or None
            if img and not (img.startswith("http://") or img.startswith("https://")):
                raise ValueError("imagen_url debe ser URL http(s)")
            db.add(models.Producto(
                sku=sku, nombre=nombre, descripcion=(row.get("descripcion") or None),
                marca=(row.get("marca") or None), unidad=unidad,
                precio_costo=precio_costo, precio_venta=precio_venta,
                stock=stock, stock_minimo=stock_min, imagen_url=img,
                activo=True, categorias=cats,
            ))
            creados += 1
        except ValueError as e:
            db.rollback()
            raise HTTPException(400, f"Fila {i}: {e}")
        except HTTPException:
            db.rollback()
            raise
    db.commit()
    return {"creados": creados, "categorias_creadas": sorted(cat_creadas)}
