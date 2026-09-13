def test_signup_creates_user_without_password_fields(client):
    r = client.post("/auth/signup", json={"username": "bob", "email": "bob@example.com", "password": "testpass123"})
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == "bob"
    assert "password" not in body
    assert "password_hash" not in body


def test_signup_duplicate_username_rejected(client):
    client.post("/auth/signup", json={"username": "bob", "email": "bob@example.com", "password": "testpass123"})
    r = client.post("/auth/signup", json={"username": "bob", "email": "other@example.com", "password": "x"})
    assert r.status_code == 409


def test_login_wrong_password_rejected(client):
    client.post("/auth/signup", json={"username": "bob", "email": "bob@example.com", "password": "testpass123"})
    r = client.post("/auth/login", json={"username": "bob", "password": "wrong"})
    assert r.status_code == 401


def test_login_nonexistent_user_same_error_as_wrong_password(client):
    r = client.post("/auth/login", json={"username": "ghost", "password": "whatever"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Incorrect username or password"


def test_login_returns_usable_token(client):
    client.post("/auth/signup", json={"username": "bob", "email": "bob@example.com", "password": "testpass123"})
    r = client.post("/auth/login", json={"username": "bob", "password": "testpass123"})
    assert r.status_code == 200
    assert "access_token" in r.json()
    assert r.json()["token_type"] == "bearer"
