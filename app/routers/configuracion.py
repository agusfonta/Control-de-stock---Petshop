from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.database import get_db
from app.deps import require_roles
from app.services.money import money

router = APIRouter(prefix="/configuracion", tags=["configuracion"])
leer = Depends(require_roles("admin", "vendedor"))
admin = Depends(require_roles("admin"))


def _obtener(db: Session) -> models.Configuracion:
    c = db.get(models.Configuracion, 1)
    if not c:
        c = models.Configuracion(id=1, margen_venta_porcentaje=0)
        db.add(c)
        db.commit()
        db.refresh(c)
    return c


@router.get("/precios", response_model=schemas.ConfiguracionPreciosOut, dependencies=[leer])
def precios(db: Session = Depends(get_db)):
    c = _obtener(db)
    return {"margen_venta_porcentaje": float(c.margen_venta_porcentaje)}


@router.patch("/precios", response_model=schemas.ConfiguracionPreciosOut, dependencies=[admin])
def actualizar_precios(d: schemas.ConfiguracionPreciosIn, db: Session = Depends(get_db)):
    c = _obtener(db)
    c.margen_venta_porcentaje = money(d.margen_venta_porcentaje)
    db.commit()
    db.refresh(c)
    return {"margen_venta_porcentaje": float(c.margen_venta_porcentaje)}
