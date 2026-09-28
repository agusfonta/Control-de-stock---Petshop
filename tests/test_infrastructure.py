"""Quick smoke tests to verify test infrastructure works."""
import pytest
from app import models
from tests.factories import create_user, create_categoria, create_producto, create_cliente, create_proveedor, seed_minimal_catalog
from tests.assertions import assert_producto_stock


def test_session_fixture_works(session):
    """Verify the session fixture provides a working DB session."""
    user = create_user(session, rol="admin", username="test_admin")
    assert user.id is not None
    assert user.rol == "admin"


def test_factory_user_creates_and_persists(session):
    user = create_user(session, rol="vendedor", username="vendor1")
    assert user.id is not None
    fetched = session.get(models.User, user.id)
    assert fetched is not None
    assert fetched.username == "vendor1"


def test_factory_categoria(session):
    cat = create_categoria(session, nombre="Test Cat")
    assert cat.id is not None
    assert cat.nombre == "Test Cat"


def test_factory_producto_with_relations(session):
    cat = create_categoria(session, nombre="Cat1")
    prov = create_proveedor(session, nombre="Prov1")
    prod = create_producto(session, nombre="Prod1", precio_venta=100, stock=5, categorias=[cat], proveedor=prov)
    assert prod.id is not None
    assert prod.categorias[0].id == cat.id
    assert prod.proveedor.id == prov.id


def test_factory_cliente_unique_email_dni(session):
    cli1 = create_cliente(session, nombre="C1", email="a@b.com", dni="111")
    cli2 = create_cliente(session, nombre="C2", email="c@d.com", dni="222")
    assert cli1.email != cli2.email
    assert cli1.dni != cli2.dni


def test_seed_minimal_catalog(session):
    data = seed_minimal_catalog(session)
    assert data["categoria"].nombre == "Alimentos"
    assert data["proveedor"].nombre == "Distribuidora Test"
    assert len(data["productos"]) == 3
    assert data["cliente"].nombre == "Cliente Test"


def test_assert_producto_stock(session):
    cat = create_categoria(session, nombre="Cat")
    prod = create_producto(session, stock=10, categorias=[cat])
    assert_producto_stock(session, prod.id, 10)
    prod.stock = 5
    session.flush()
    assert_producto_stock(session, prod.id, 5)