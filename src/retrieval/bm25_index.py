"""
Index BM25 pour CustomsRAG.

Alternative aux embeddings denses (sentence-transformers) qui necessitent
de telecharger des poids de modele depuis HuggingFace/S3 - indisponible
dans certains environnements sandboxes/air-gapped. BM25 est un algorithme
de recherche lexicale classique (pas de reseau de neurones, pas de
telechargement), tres performant sur du vocabulaire exact comme les codes
SH ("0406.10 00") ou les numeros d'article ("Art. 145") que des embeddings
dense peuvent parfois diluer.

En production (avec acces internet normal), ce module peut cohabiter avec
un index dense (voir build_dense_index.py) pour faire du retrieval hybride
BM25 + embeddings, une pratique courante en RAG juridique/reglementaire.
"""

import json
import pickle
import re
import sys
import unicodedata
from pathlib import Path

from rank_bm25 import BM25Okapi

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.rag.i18n import detect_language, expand_query

BASE_DIR = Path(__file__).resolve().parents[2]
CODE_CHUNKS_PATH = BASE_DIR / "data" / "processed" / "code_douanes_chunks.json"
TARIF_CHUNKS_PATH = BASE_DIR / "data" / "processed" / "tarif_douanes_chunks.json"
INDEX_PATH = BASE_DIR / "data" / "vector_store" / "bm25_index.pkl"

# Mots vides francais courants a ignorer pour ne pas polluer le score BM25
STOPWORDS = set("""
le la les un une des du de d l et ou a au aux en dans sur pour par avec
sans sous entre ce cet cette ces qui que quoi dont ou est sont etre a ete
son sa ses leur leurs il elle ils elles nous vous je tu on plus moins tres
""".split())


def normalize(text: str) -> str:
    """Minuscules + suppression des accents, pour un matching plus robuste
    (utile vu que les PDF melangent parfois accents et non-accents selon
    l'encodage d'origine)."""
    text = text.lower()
    # NFKD ne decompose PAS les ligatures ϒ/æ (ce ne sont pas des caracteres
    # accentues combinants) : sans ce remplacement manuel, "œufs" devient
    # "ufs" apres tokenisation et ne matche plus jamais la saisie usuelle
    # "oeufs" tapee au clavier standard.
    text = text.replace("œ", "oe").replace("æ", "ae")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text


def tokenize(text: str) -> list[str]:
    text = normalize(text)
    # Garde les codes SH du type 0406.10 comme un seul token (le point est
    # significatif), separe le reste sur la ponctuation/espaces.
    tokens = re.findall(r"\d{2,4}\.\d{2}(?:\.?\d{2})?|[a-z]+", text)
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def load_corpus():
    """Charge les deux jeux de chunks et construit une liste unifiee de
    documents avec un texte de recherche et les metadonnees d'origine."""
    documents = []

    code_chunks = json.loads(CODE_CHUNKS_PATH.read_text(encoding="utf-8"))
    for c in code_chunks:
        documents.append({
            "id": f"code:{c['article']}",
            "source_type": "code_douanes",
            "text": c["text"],
            "label": f"Code des Douanes, {c['article']}" + (f" ({c['chapitre']})" if c.get("chapitre") else ""),
            "metadata": c,
        })

    tarif_chunks = json.loads(TARIF_CHUNKS_PATH.read_text(encoding="utf-8"))
    for c in tarif_chunks:
        if c["type"] == "note_explicative":
            label = f"Tarif des Douanes, note explicative (Chapitre {c.get('chapitre')})"
            search_text = c["text"]
        else:
            label = f"Tarif des Douanes, code SH {c.get('code_sh')}"
            # Les designations comme "Autres" ou "Frais" n'ont de sens que
            # rattachees a leur position/sous-position parente (ex: "0407
            # Oeufs d'oiseaux" > "Autres oeufs frais" > "Autres"). On les
            # prefixe au texte indexe pour que la recherche les retrouve
            # meme quand la ligne elle-meme est un designation generique.
            context_parts = [
                c.get("chapitre_titre"),
                c.get("position_sh"),
                c.get("sous_position_sh"),
            ]
            context = " - ".join(p for p in context_parts if p)
            search_text = f"{context} - {c['text']}" if context else c["text"]
        documents.append({
            "id": f"tarif:{c.get('code_sh') or c.get('page')}:{len(documents)}",
            "source_type": "tarif_douanes",
            "text": search_text,
            "label": label,
            "metadata": c,
        })

    return documents


def build_index():
    print("Chargement du corpus...")
    documents = load_corpus()
    print(f"{len(documents)} documents charges")

    print("Tokenisation...")
    tokenized_corpus = [tokenize(d["text"]) for d in documents]

    print("Construction de l'index BM25...")
    bm25 = BM25Okapi(tokenized_corpus)

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_PATH, "wb") as f:
        pickle.dump({"bm25": bm25, "documents": documents}, f)
    print(f"Index sauvegarde dans {INDEX_PATH} ({INDEX_PATH.stat().st_size / 1024:.0f} KB)")

    return bm25, documents


def load_index():
    with open(INDEX_PATH, "rb") as f:
        data = pickle.load(f)
    return data["bm25"], data["documents"]


def query(question: str, top_k: int = 5, bm25=None, documents=None):
    if bm25 is None or documents is None:
        bm25, documents = load_index()
    lang = detect_language(question)
    expanded_question = expand_query(question, lang)
    tokens = tokenize(expanded_question)
    scores = bm25.get_scores(tokens)
    ranked = sorted(range(len(scores)), key=lambda i: -scores[i])[:top_k]
    results = []
    for i in ranked:
        results.append({
            "score": round(float(scores[i]), 3),
            "label": documents[i]["label"],
            "text": documents[i]["text"],
            "metadata": documents[i]["metadata"],
        })
    return results


if __name__ == "__main__":
    bm25, documents = build_index()

    print("\n=== Tests de requetes ===")
    test_questions = [
        "quel est le taux de droit de douane pour importer du fromage",
        "quelles sont les sanctions en cas de fraude douaniere",
        "code SH pour le miel naturel",
        "definition des lois et reglements douaniers",
    ]
    for q in test_questions:
        print(f"\n--- Question: {q} ---")
        results = query(q, top_k=3, bm25=bm25, documents=documents)
        for r in results:
            print(f"  [{r['score']}] {r['label']}")
            print(f"      {r['text'][:120]}")
