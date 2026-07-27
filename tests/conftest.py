import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.retrieval.bm25_index import load_index


@pytest.fixture(scope="session")
def bm25_and_docs():
    """Charge l'index BM25 une seule fois pour toute la session de tests
    (fichier de 5+ Mo, evite de le recharger a chaque test)."""
    bm25, documents = load_index()
    return bm25, documents
