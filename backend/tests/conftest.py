import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Community, Post, User  # noqa: F401 -- registers tables

TEST_DATABASE_URL = settings.database_url.rsplit("/", 1)[0] + "/reddit_clone_v3_test"

engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_TABLES_IN_DELETE_ORDER = ["posts", "communities", "users"]


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _clean_database():
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {', '.join(_TABLES_IN_DELETE_ORDER)} RESTART IDENTITY CASCADE"))
    yield


def _override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Signs up + logs in a user, returns headers ready to use."""
    client.post("/auth/signup", json={"username": "alice", "email": "alice@example.com", "password": "testpass123"})
    r = client.post("/auth/login", json={"username": "alice", "password": "testpass123"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
