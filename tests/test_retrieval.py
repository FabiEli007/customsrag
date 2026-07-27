from src.retrieval.bm25_index import query, tokenize
from src.rag.i18n import detect_language


def test_retrieval_finds_exact_hs_code_match(bm25_and_docs):
    """Question ciblee sur un produit precis -> le bon code SH doit sortir
    en position 1, pas juste 'quelque part dans le top 5'."""
    bm25, documents = bm25_and_docs
    results = query("code SH pour le miel naturel", top_k=5, bm25=bm25, documents=documents)
    assert results[0]["metadata"].get("code_sh") == "0409.00 00"


def test_retrieval_finds_relevant_article(bm25_and_docs):
    """Note : une requete generique comme 'definition des droits de
    douane' ne suffit pas a isoler un article precis, car cette expression
    apparait dans la quasi-totalite des 465 articles du Code - c'est une
    limite connue du BM25 pur (cf. README, 'Limites connues'). On teste
    donc avec une formulation reprenant du vocabulaire distinctif reellement
    present dans l'article cible, ce qui est le regime pour lequel BM25 est
    fait."""
    bm25, documents = bm25_and_docs
    results = query(
        "proteger le commerce l'industrie et l'agriculture de Madagascar",
        top_k=3, bm25=bm25, documents=documents,
    )
    assert results[0]["metadata"].get("article") == "Art. 2"


def test_oe_ligature_matches_regular_spelling(bm25_and_docs):
    """Regression test pour le bug de tokenisation de la ligature 'oe'
    (cf. README - 'oeufs' devenait 'ufs' et ne matchait plus rien)."""
    bm25, documents = bm25_and_docs
    results_ligature = query("prix des œufs frais", top_k=3, bm25=bm25, documents=documents)
    results_plain = query("prix des oeufs frais", top_k=3, bm25=bm25, documents=documents)
    assert results_ligature[0]["label"] == results_plain[0]["label"]


def test_tokenize_strips_accents_and_stopwords():
    tokens = tokenize("Quel est le taux de droit de douane ?")
    assert "le" not in tokens
    assert "taux" in tokens
    assert "droit" in tokens


def test_language_detection_french():
    assert detect_language("Quel est le taux de TVA sur le fromage ?") == "fr"


def test_language_detection_english():
    assert detect_language("What is the customs duty rate on cheese?") == "en"


def test_language_detection_malagasy():
    assert detect_language("Firy ny hetra amin'ny tantely?") == "mg"
