import os

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_endpoint_reports_index_loaded(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["index_loaded"] is True
    assert body["documents_count"] > 5000


def test_sources_stats_breaks_down_by_type(client):
    response = client.get("/sources/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["par_source"]["code_douanes"] > 0
    assert body["par_source"]["tarif_douanes"] > 0


def test_ask_rejects_too_short_question(client):
    response = client.post("/ask", json={"question": "hi"})
    assert response.status_code == 422


def test_ask_without_api_key_degrades_gracefully(client, monkeypatch):
    """Sans cle API, l'endpoint ne doit jamais planter (500) : il doit
    repondre 200 en mode extractif."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    response = client.post("/ask", json={"question": "quel est le taux pour le miel"})
    assert response.status_code == 200
    assert response.json()["mode"] in ("extractif", "aucun_resultat")
