def test_register_sets_cookie_and_me_works(client):
    r = client.post(
        "/api/auth/register", json={"email": "a@b.com", "password": "secret123"}
    )
    assert r.status_code == 201
    assert r.json()["email"] == "a@b.com"
    assert "pt_session" in r.cookies

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "a@b.com"


def test_register_duplicate_email_409(client):
    payload = {"email": "a@b.com", "password": "secret123"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 409


def test_register_short_password_422(client):
    r = client.post("/api/auth/register", json={"email": "a@b.com", "password": "short"})
    assert r.status_code == 422


def test_login_wrong_password_401(client):
    client.post("/api/auth/register", json={"email": "a@b.com", "password": "secret123"})
    client.post("/api/auth/logout")
    r = client.post("/api/auth/login", json={"email": "a@b.com", "password": "wrong-pass"})
    assert r.status_code == 401


def test_login_then_logout_clears_access(client):
    client.post("/api/auth/register", json={"email": "a@b.com", "password": "secret123"})
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401

    r = client.post("/api/auth/login", json={"email": "a@b.com", "password": "secret123"})
    assert r.status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_me_unauthenticated_401(client):
    assert client.get("/api/auth/me").status_code == 401
