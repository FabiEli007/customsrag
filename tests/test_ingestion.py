import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"


def load_code_chunks():
    return json.loads((DATA_DIR / "code_douanes_chunks.json").read_text(encoding="utf-8"))


def load_tarif_chunks():
    return json.loads((DATA_DIR / "tarif_douanes_chunks.json").read_text(encoding="utf-8"))


def test_code_douanes_has_expected_volume():
    """Garde-fou anti-regression : si un futur changement du parser fait
    chuter drastiquement le nombre d'articles extraits, ce test le detecte
    immediatement plutot que de le decouvrir en production."""
    chunks = load_code_chunks()
    assert len(chunks) > 400, "Nombre d'articles extraits anormalement bas"


def test_tarif_douanes_has_expected_volume():
    chunks = load_tarif_chunks()
    lignes = [c for c in chunks if c["type"] == "ligne_tarifaire"]
    assert len(lignes) > 4000, "Nombre de lignes tarifaires anormalement bas"


def test_code_chunks_have_required_fields():
    chunks = load_code_chunks()
    for c in chunks[:50]:  # echantillon, pas les 465 pour la vitesse
        assert c["article"], "Article sans identifiant"
        assert c["text"], f"Article {c['article']} sans texte"
        assert c["chapitre"] is not None, f"Article {c['article']} sans chapitre assigne"


def test_tarif_lines_have_rates():
    """Chaque ligne tarifaire complete doit porter un taux DD (le coeur de
    l'info recherchee par un utilisateur)."""
    chunks = load_tarif_chunks()
    lignes = [c for c in chunks if c["type"] == "ligne_tarifaire"]
    sample = lignes[:100]
    missing = [c for c in sample if not c.get("dd")]
    assert not missing, f"{len(missing)} lignes tarifaires sans taux DD dans l'echantillon"


def test_no_exact_text_duplicates_in_code():
    """Le Code reimprime parfois un meme numero d'article a plusieurs
    reprises avec des references de loi differentes (versions avant/apres
    amendement) - ce n'est PAS un doublon, chaque occurrence a un texte
    different. Ce test verifie l'absence de vrais doublons : texte
    strictement identique associe au meme article (signe d'un chevauchement
    d'extraction sur une frontiere de page)."""
    chunks = load_code_chunks()
    seen = set()
    duplicates = []
    for c in chunks:
        key = (c["article"], c["text"])
        if key in seen:
            duplicates.append(c["article"])
        seen.add(key)
    assert not duplicates, f"Doublons de texte exact detectes : {duplicates}"
