from app.core.time import local_day_bounds_utc
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app import models, schemas
from app.deps import require_roles
from app.services import cash as cash_service
from app.services.money import money

router = APIRouter(prefix="/caja", tags=["caja"])
leer = Depends(require_roles("admin", "vendedor"))


def _parse_fecha(s: str):
    try:
        from datetime import datetime
        return datetime.fromisoformat(s).date()
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
        ini, fin = local_day_bounds_utc(_parse_fecha(fecha))
        q = q.filter(models.MovimientoCaja.fecha >= ini,
                     models.MovimientoCaja.fecha < fin)
    movs = q.limit(500).all()
    total_e = money(sum((m.monto for m in movs if m.tipo == models.TipoMovCaja.ENTRADA), money(0)))
    total_s = money(sum((m.monto for m in movs if m.tipo == models.TipoMovCaja.SALIDA), money(0)))
    por_medio: dict[str, dict[str, object]] = {}
    for m in movs:
        d = por_medio.setdefault(m.medio.value, {"entrada": money(0), "salida": money(0)})
        d["entrada" if m.tipo == models.TipoMovCaja.ENTRADA else "salida"] = money(
            d["entrada" if m.tipo == models.TipoMovCaja.ENTRADA else "salida"] + m.monto)
    return {"movimientos": [_out(m) for m in movs],
            "total_entrada": total_e, "total_salida": total_s,
            "balance": money(total_e - total_s), "por_medio": por_medio}



@router.get("/mensual", dependencies=[leer])
def resumen_mensual(mes: str | None = None, db: Session = Depends(get_db)):
    from datetime import date, datetime
    from calendar import monthrange
    objetivo = mes or datetime.now().strftime("%Y-%m")
    try:
        year, month = [int(x) for x in objetivo.split("-")]
        inicio = date(year, month, 1)
        fin = date(year, month, monthrange(year, month)[1])
    except (ValueError, TypeError):
        raise HTTPException(422, "Mes inválido: usar YYYY-MM")
    ini_utc = local_day_bounds_utc(inicio)[0]
    fin_utc = local_day_bounds_utc(fin)[1]
    movs = db.query(models.MovimientoCaja).filter(
        models.MovimientoCaja.fecha >= ini_utc,
        models.MovimientoCaja.fecha < fin_utc,
    ).order_by(models.MovimientoCaja.fecha, models.MovimientoCaja.id).all()
    total_e = money(sum((m.monto for m in movs if m.tipo == models.TipoMovCaja.ENTRADA), money(0)))
    total_s = money(sum((m.monto for m in movs if m.tipo == models.TipoMovCaja.SALIDA), money(0)))
    por_dia = {}
    for m in movs:
        dia = m.fecha.date().isoformat()
        item = por_dia.setdefault(dia, {"entrada": money(0), "salida": money(0)})
        if m.tipo == models.TipoMovCaja.ENTRADA:
            item["entrada"] = money(item["entrada"] + m.monto)
        else:
            item["salida"] = money(item["salida"] + m.monto)
    for item in por_dia.values():
        item["balance"] = money(item["entrada"] - item["salida"])
    return {
        "mes": objetivo,
        "total_entrada": total_e,
        "total_salida": total_s,
        "balance": money(total_e - total_s),
        "por_dia": [{"fecha": k, **v} for k, v in sorted(por_dia.items())],
    }

@router.post("", response_model=schemas.MovimientoCajaOut, status_code=201, dependencies=[leer])
def crear(d: schemas.MovimientoCajaCreate, db: Session = Depends(get_db)):
    try:
        movimiento = cash_service.crear_manual(db, d)
    except cash_service.CashError as e:
        db.rollback()
        raise HTTPException(e.status_code, e.detail)
    return _out(movimiento)


@router.delete("/{mid}", status_code=204, dependencies=[leer])
def eliminar(mid: int, db: Session = Depends(get_db)):
    try:
        cash_service.eliminar_manual(db, mid)
    except cash_service.CashError as e:
        db.rollback()
        raise HTTPException(e.status_code, e.detail)
    return None
