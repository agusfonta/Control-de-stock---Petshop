"""Pytest configuration and fixtures for PetShop tests."""
import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import Base, get_db
from app.models import User
from app.core.security import create_token, hash_password

TEST_PASSWORD = "test123"


@pytest.fixture(scope="session")
def engine():
    """Session-scoped SQLite in-memory engine with schema creation."""
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture(scope="function")
def session(engine):
    """Function-scoped DB session with transaction rollback for isolation."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
async def client(session):
    """AsyncClient with get_db overridden to use test session."""
    def _get_db_override():
        yield session

    app.dependency_overrides[get_db] = _get_db_override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_headers(session):
    """Returns a dict with Authorization header for a given role."""
    users = {}

    def _auth_headers(role: str):
        if role not in users:
            username = role
            user = session.query(User).filter(User.username == username).first()
            if not user:
                user = User(username=username, hashed_password=hash_password(TEST_PASSWORD), rol=role, activo=True)
                session.add(user)
                session.commit()
                session.refresh(user)
            users[role] = user
        token = create_token(users[role].username, users[role].rol)
        return {"Authorization": f"Bearer {token}"}

    return _auth_headers


@pytest.fixture(scope="function")
def admin_headers(auth_headers):
    return auth_headers("admin")


@pytest.fixture(scope="function")
def vendedor_headers(auth_headers):
    return auth_headers("vendedor")