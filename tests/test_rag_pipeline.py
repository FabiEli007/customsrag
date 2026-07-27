import os

import pytest

from src.rag.generate import answer_question

# Ces tests forcent le mode extractif (pas de cle API requise), ce qui les
# rend executables tels quels en CI sans depenser de credit Anthropic.


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_out_of_scope_question_returns_not_found():
    """Question hors perimetre (TVA en France, pas Madagascar) -> le
    systeme doit refuser plutot que d'afficher un article sans rapport
    avec assurance. C'est le garde-fou anti-hallucination le plus
    important du projet."""
    result = answer_question("quel est le taux de TVA en France")
    assert result["mode"] == "aucun_resultat"
    assert result["sources"] == []


def test_unrelated_general_knowledge_question_returns_not_found():
    result = answer_question("quelle est la capitale de Madagascar")
    assert result["mode"] == "aucun_resultat"


def test_relevant_question_returns_extractive_answer_with_sources():
    result = answer_question("quel est le taux de droit de douane pour le fromage")
    assert result["mode"] == "extractif"
    assert len(result["sources"]) > 0
    assert "0406" in result["answer"] or "fromage" in result["answer"].lower()


def test_answer_language_matches_question_language():
    result_en = answer_question("what is the customs duty on horses")
    assert result_en["language"] == "en"

    result_mg = answer_question("firy ny hetra amin'ny tantely")
    assert result_mg["language"] == "mg"
