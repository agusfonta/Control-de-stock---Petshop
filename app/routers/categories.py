from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app import models, schemas
from app.deps import require_roles

router = APIRouter(prefix="/categorias", tags=["categorias"])
leer = Depends(require_roles("admin", "vendedor"))
admin = Depends(require_roles("admin"))

@router.post("", response_model=schemas.CategoriaOut, status_code=201, dependencies=[leer])
def crear(d: schemas.CategoriaCreate, db: Session = Depends(get_db)):
    if db.query(models.Categoria).filter(models.Categoria.nombre == d.nombre).first():
        raise HTTPException(400, "Categoria ya existe")
    c = models.Categoria(nombre=d.nombre, descripcion=d.descripcion)
    db.add(c); db.commit(); db.refresh(c)
    return c

@router.get("", response_model=list[schemas.CategoriaOut], dependencies=[leer])
def listar(db: Session = Depends(get_db)):
    return db.query(models.Categoria).order_by(models.Categoria.nombre).all()

@router.get("/{cid}", response_model=schemas.CategoriaOut, dependencies=[leer])
def obtener(cid: int, db: Session = Depends(get_db)):
    c = db.get(models.Categoria, cid)
    if not c: raise HTTPException(404, "Categoria no encontrada")
    return c

@router.put("/{cid}", response_model=schemas.CategoriaOut, dependencies=[leer])
def actualizar(cid: int, d: schemas.CategoriaCreate, db: Session = Depends(get_db)):
    c = db.get(models.Categoria, cid)
    if not c: raise HTTPException(404, "Categoria no encontrada")
    otro = db.query(models.Categoria).filter(models.Categoria.nombre == d.nombre, models.Categoria.id != cid).first()
    if otro:
        raise HTTPException(400, "Ya existe otra categoria con ese nombre")
    c.nombre = d.nombre; c.descripcion = d.descripcion
    db.commit(); db.refresh(c)
    return c

@router.delete("/{cid}", status_code=204, dependencies=[admin])
def eliminar(cid: int, db: Session = Depends(get_db)):
    c = db.get(models.Categoria, cid)
    if not c: raise HTTPException(404, "Categoria no encontrada")
    # Los productos NO se borran: quedan "Sin categoría" y se les puede
    # asignar otra desde el panel (PATCH /productos/{id}).
    db.delete(c); db.commit()
    return None
