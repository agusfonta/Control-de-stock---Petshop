"""Migración pago múltiple: crea `pagos_pedido` y backfill desde `pedidos`.

Bases nuevas no la necesitan (`Base.metadata.create_all` ya crea la tabla).
Idempotente en SQLite y Postgres. Reversible con `--rollback`.

Uso:
  python scripts/migrate_pagos_pedido.py [--db URL]
  python scripts/migrate_pagos_pedido.py --rollback [--db URL]
"""
import argparse

from sqlalchemy import create_engine, text

import app.models  # noqa: F401 - registra PagoPedido en Base.metadata
from app.core.config import settings
from app.core.database import Base, _norm_url


def main() -> None:
    ap = argparse.ArgumentParser(description="Migra pagos_pedido (pago múltiple por venta).")
    ap.add_argument("--db", default=None, help="DATABASE_URL (default: la de settings/.env)")
    ap.add_argument("--rollback", action="store_true", help="Elimina pagos_pedido")
    args = ap.parse_args()

    url = _norm_url(args.db or settings.database_url)
    eng = create_engine(
        url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {}
    )
    tbl = Base.metadata.tables["pagos_pedido"]
    with eng.begin() as conn:
        if args.rollback:
            tbl.drop(bind=conn, checkfirst=True)
            print("rollback ok: pagos_pedido eliminada")
            return
        tbl.create(bind=conn, checkfirst=True)
        n = conn.execute(
            text(
                "INSERT INTO pagos_pedido (pedido_id, metodo, monto) "
                "SELECT p.id, p.metodo_pago, p.total FROM pedidos p "
                "WHERE NOT EXISTS (SELECT 1 FROM pagos_pedido pp WHERE pp.pedido_id = p.id)"
            )
        ).rowcount
        print(f"migración ok: tabla verificada, {n} pagos backfill")


if __name__ == "__main__":
    main()
