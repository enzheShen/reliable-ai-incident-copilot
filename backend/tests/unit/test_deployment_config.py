from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings, sqlalchemy_database_url
from app.frontend import mount_frontend
from app.providers import RuleBasedFallbackProvider
from app.services.analysis import configured_primary_provider


@pytest.mark.parametrize("prefix", ["postgres://", "postgresql://"])
def test_neon_database_url_uses_psycopg3(prefix: str) -> None:
    settings = Settings(
        _env_file=None,
        database_url=f"{prefix}demo:secret@example.neon.tech/app?sslmode=require",
    )
    assert settings.database_url == (
        "postgresql+psycopg://demo:secret@example.neon.tech/app?sslmode=require"
    )


def test_explicit_sqlalchemy_database_url_is_unchanged() -> None:
    value = "postgresql+psycopg://demo:secret@localhost/app"
    settings = Settings(_env_file=None, database_url=value)
    assert settings.database_url == value


def test_migration_url_normalizer_matches_application_driver() -> None:
    value = "postgresql://demo:p%40ss@example.neon.tech/app?sslmode=require"
    assert sqlalchemy_database_url(value) == (
        "postgresql+psycopg://demo:p%40ss@example.neon.tech/app?sslmode=require"
    )


def test_rule_mode_selects_non_billable_provider() -> None:
    provider = configured_primary_provider(Settings(_env_file=None, llm_mode="rules"))
    assert isinstance(provider, RuleBasedFallbackProvider)


def test_unknown_provider_mode_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, llm_mode="surprise")


def test_spa_routes_fall_back_without_masking_api_404(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<h1>Incident Copilot</h1>", encoding="utf-8")
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("console.log('ok')", encoding="utf-8")

    app = FastAPI()

    @app.get("/api/v1/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    mount_frontend(app, tmp_path, required=True)
    client = TestClient(app)

    assert client.get("/").status_code == 200
    assert client.get("/history").text == "<h1>Incident Copilot</h1>"
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/api/v1/ping").json() == {"status": "ok"}
    assert client.get("/api/v1/missing").status_code == 404


def test_production_requires_frontend_build(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="frontend build is missing"):
        mount_frontend(FastAPI(), tmp_path / "missing", required=True)
