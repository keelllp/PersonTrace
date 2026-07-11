from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def make_dist(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>PersonTrace SPA</html>")
    (dist / "assets" / "app.js").write_text("console.log('pt')")
    return dist


def test_spa_fallback_serves_index_for_client_routes(tmp_path):
    app = create_app(spa_dist=make_dist(tmp_path))
    client = TestClient(app)
    for path in ("/", "/login", "/traces/abc123"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert "PersonTrace SPA" in r.text

    assert client.get("/assets/app.js").status_code == 200
    # API routes are untouched by the fallback
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/auth/me").status_code == 401


def test_no_dist_no_spa(tmp_path):
    app = create_app(spa_dist=tmp_path / "missing")
    client = TestClient(app)
    assert client.get("/").status_code == 404
    assert client.get("/api/health").status_code == 200
