from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.core.config import settings
from app.core.database import Base, engine
from app import models  # noqa: registra modelos
from app.routers import categories, products, customers, orders, inventory, auth

Base.metadata.create_all(bind=engine)

if settings.secret_key == "cambiar-en-produccion-petshop-demo-2026":
    logging.getLogger("uvicorn").warning(
        "SEGURIDAD: usando SECRET_KEY de demo. Definí SECRET_KEY en .env para producción."
    )

app = FastAPI(title="PetShop Stock API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(products.router)
app.include_router(customers.router)
app.include_router(orders.router)
app.include_router(inventory.router)
app.include_router(inventory.prov)
app.include_router(inventory.rep)

@app.get("/health")
def health():
    return {"ok": True, "demo": "Swagger en /docs"}
