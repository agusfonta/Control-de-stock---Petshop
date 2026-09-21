"""Seed demo petshop."""
from app.core.database import SessionLocal, Base, engine
from app import models
from app.core.security import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()

if not db.query(models.Categoria).first():
    alimentos = models.Categoria(nombre="Alimentos", descripcion="Comida para mascotas")
    juguetes = models.Categoria(nombre="Juguetes", descripcion="Juguetes y entretenimiento")
    higiene = models.Categoria(nombre="Higiene", descripcion="Cuidado e higiene")
    db.add_all([alimentos, juguetes, higiene]); db.commit()
    p1 = models.Producto(sku="RC-MINI-3KG", nombre="Royal Canin Mini 3kg", descripcion="Alimento perro adulto raza pequeña",
    marca="Royal Canin", unidad=models.Unidad.kg, precio_costo=18000, precio_venta=24999,
    stock=25, stock_minimo=10, activo=True, categorias=[alimentos])
    p2 = models.Producto(sku="RC-MINI-10KG", nombre="Royal Canin Mini 10kg", descripcion="Alimento perro adulto raza pequeña x10kg",
    marca="Royal Canin", unidad=models.Unidad.kg, precio_costo=52000, precio_venta=69999,
    stock=8, stock_minimo=10, activo=True, categorias=[alimentos])
    p3 = models.Producto(sku="PELOTA-01", nombre="Pelota resistente", descripcion="Pelota para perros",
    marca="PetFun", unidad=models.Unidad.unidad, precio_costo=1500, precio_venta=3499,
    stock=50, stock_minimo=10, activo=True, categorias=[juguetes])
    db.add_all([p1, p2, p3])
    db.add(models.Cliente(nombre="Demo Cliente", email="demo@petshop.com", telefono="11-1234-5678", dni="30123456", direccion="Av Demo 123"))
    db.add(models.User(username="admin", hashed_password=hash_password("admin123"), rol="admin"))
    db.commit()
    print("Seed OK: 3 categorias, 3 productos (1 con stock bajo), 1 cliente, admin/admin123")
else:
    print("Seed ya existente")
db.close()
