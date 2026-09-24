from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app import models, schemas
from app.deps import require_roles

router = APIRouter(prefix="/caja", tags=["caja"])
leer = Depends(require_roles("admin", "vendedor"))


def _parse_fecha(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        raise HTTPException(422, f"Fecha inválida '{s}': usar formato YYYY-MM-DD")


def _out(m: models.MovimientoCaja) -> schemas.MovimientoCajaOut:
    o = schemas.MovimientoCajaOut.model_validate(m)
    o.automatico = m.pedido_id is not None or m.descripcion.startswith("Pago ")
    return o


@router.get("", dependencies=[leer])
def resumen(fecha: str | None = None, db: Session = Depends(get_db)):
    """Caja del día: entradas/salidas, totales y desglose por medio (EF/MP/DB/CD/TR)."""
    q = db.query(models.MovimientoCaja).order_by(models.MovimientoCaja.fecha, models.MovimientoCaja.id)
    if fecha:
        ini = _parse_fecha(fecha)
        q = q.filter(models.MovimientoCaja.fecha >= ini,
                     models.MovimientoCaja.fecha < ini + timedelta(days=1))
    movs = q.limit(500).all()
    total_e = round(sum(m.monto for m in movs if m.tipo == models.TipoMovCaja.ENTRADA), 2)
    total_s = round(sum(m.monto for m in movs if m.tipo == models.TipoMovCaja.SALIDA), 2)
    por_medio: dict[str, dict[str, float]] = {}
    for m in movs:
        d = por_medio.setdefault(m.medio.value, {"entrada": 0.0, "salida": 0.0})
        d["entrada" if m.tipo == models.TipoMovCaja.ENTRADA else "salida"] = round(
            d["entrada" if m.tipo == models.TipoMovCaja.ENTRADA else "salida"] + m.monto, 2)
    return {"movimientos": [_out(m) for m in movs],
            "total_entrada": total_e, "total_salida": total_s,
            "balance": round(total_e - total_s, 2), "por_medio": por_medio}


@router.post("", response_model=schemas.MovimientoCajaOut, status_code=201, dependencies=[leer])
def crear(d: schemas.MovimientoCajaCreate, db: Session = Depends(get_db)):
    """Movimiento manual (gastos como Cabify/estanterías, o entradas extra)."""
    m = models.MovimientoCaja(
        tipo=d.tipo, medio=d.medio, descripcion=d.descripcion.strip(),
        monto=d.monto, fecha=d.fecha or datetime.utcnow())
    db.add(m); db.commit(); db.refresh(m)
    return _out(m)


@router.delete("/{mid}", status_code=204, dependencies=[leer])
def eliminar(mid: int, db: Session = Depends(get_db)):
    """Solo manuales: los automáticos (ventas/pagos) se anulan con la operación origen."""
    m = db.get(models.MovimientoCaja, mid)
    if not m:
        raise HTTPException(404, "Movimiento no encontrado")
    if _out(m).automatico:
        raise HTTPException(400, "Movimiento automático: no se borra, se anula desde la venta/pago origen")
    db.delete(m); db.commit()
    return None
