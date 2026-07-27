"""
Coeur du RAG CustomsRAG : question utilisateur -> retrieval BM25 ->
prompt contextualise -> generation Claude avec citation des sources.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python3 src/rag/generate.py "quel est le taux de droit de douane pour le fromage ?"

Ou en import :
    from src.rag.generate import answer_question
    result = answer_question("...")
"""

import os
import sys
from pathlib import Path

import anthropic

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.retrieval.bm25_index import load_index, query as bm25_query
from src.rag.i18n import detect_language, expand_query, UI_PHRASES

# Modele : Haiku est largement suffisant pour de la Q&A a contexte fourni
# (le gros du travail est fait par le retrieval, pas par le raisonnement),
# et beaucoup moins couteux que Sonnet/Opus pour un usage repete.
MODEL = "claude-haiku-4-5-20251001"
TOP_K = 5

# En-dessous de ce score BM25, le meilleur resultat trouve est trop faible
# pour etre presente comme une reponse fiable (cas typique : question hors
# perimetre - "TVA en France", "capitale de Madagascar" - qui partage juste
# quelques mots avec le corpus sans rapport reel). Calibre empiriquement :
# les questions pertinentes du corpus scorent generalement >= 10-12, les
# questions hors sujet plafonnent autour de 7-9.
MIN_RELEVANT_SCORE = 10.0

SYSTEM_PROMPT = """Tu es un assistant specialise dans la reglementation douaniere et tarifaire de Madagascar.

Regles strictes :
1. Reponds UNIQUEMENT a partir des extraits fournis ci-dessous (Code des Douanes et Tarif des Douanes). N'utilise aucune connaissance externe.
2. Cite systematiquement ta source precise entre parentheses : le numero d'article (ex: "Art. 145 du Code des Douanes") ou le code SH (ex: "code SH 0406.10 00 du Tarif des Douanes").
3. Si les extraits fournis ne permettent pas de repondre a la question, dis-le clairement dans la langue de la question. Ne devine jamais.
4. Reponds TOUJOURS dans la meme langue que la question posee (francais, anglais ou malgache). Les extraits fournis sont en francais (langue de reference legale) : traduis le contenu de ta reponse dans la langue de la question, mais garde les numeros d'article et codes SH tels quels (ils ne se traduisent pas).
5. Sois concis et direct.
6. Si plusieurs taux ou dispositions semblent pertinents, presente-les tous plutot que d'en choisir un arbitrairement.
"""


def build_context_block(results: list[dict]) -> str:
    blocks = []
    for i, r in enumerate(results, start=1):
        blocks.append(f"[Extrait {i} - {r['label']}]\n{r['text']}")
    return "\n\n".join(blocks)


def build_extractive_answer(results: list[dict], language: str = "fr") -> str:
    """Reponse degradee, sans appel LLM : reformate directement le(s)
    meilleur(s) extrait(s) trouve(s) par le retrieval. Utile quand l'API
    Claude est indisponible (pas de credit, pas de cle, quota depasse) -
    le systeme reste utilisable plutot que de tomber en erreur.

    Le contenu regulatoire lui-meme reste en francais (impossible a
    traduire sans LLM) ; seul l'habillage (libelles fixes) est traduit,
    avec une note explicite pour que ce soit transparent pour l'utilisateur."""
    phrases = UI_PHRASES.get(language, UI_PHRASES["fr"])
    top = results[0]
    lines = [
        f"{phrases['extractive_header']} {phrases['source_note']}\n",
        f"{phrases['according_to']} {top['label']} :\n{top['text']}",
    ]

    autres = [r for r in results[1:3] if r["score"] > 0]
    if autres:
        lines.append(f"\n{phrases['other_extracts']}")
        for r in autres:
            lines.append(f"- {r['label']} : {r['text'][:200]}")

    return "\n".join(lines)


def answer_question(question: str, top_k: int = TOP_K, model: str = MODEL) -> dict:
    language = detect_language(question)
    search_query = expand_query(question, language)

    bm25, documents = load_index()
    results = bm25_query(search_query, top_k=top_k, bm25=bm25, documents=documents)

    if not results or all(r["score"] <= 0 for r in results):
        phrases = UI_PHRASES.get(language, UI_PHRASES["fr"])
        return {
            "question": question,
            "answer": phrases["not_found"],
            "sources": [],
            "mode": "aucun_resultat",
            "language": language,
        }

    context = build_context_block(results)
    user_message = f"""Extraits de reference :

{context}

---

Question ({language}) : {question}"""

    sources = [{"label": r["label"], "score": r["score"]} for r in results]
    phrases = UI_PHRASES.get(language, UI_PHRASES["fr"])
    best_score = results[0]["score"]

    if not os.environ.get("ANTHROPIC_API_KEY"):
        if best_score < MIN_RELEVANT_SCORE:
            # Pas de LLM disponible pour juger la pertinence reelle de
            # l'extrait : plutot que d'afficher un article hors-sujet comme
            # s'il repondait a la question, on l'assume honnetement.
            return {
                "question": question,
                "answer": phrases["not_found"],
                "sources": [],
                "mode": "aucun_resultat",
                "language": language,
            }
        return {
            "question": question,
            "answer": build_extractive_answer(results, language),
            "sources": sources,
            "mode": "extractif",
            "language": language,
        }

    try:
        client = anthropic.Anthropic()  # lit ANTHROPIC_API_KEY depuis l'environnement
        response = client.messages.create(
            model=model,
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        answer_text = "".join(
            block.text for block in response.content if block.type == "text"
        )
        return {
            "question": question,
            "answer": answer_text,
            "sources": sources,
            "mode": "generatif",
            "language": language,
        }
    except anthropic.APIError as e:
        # Pas de credit, cle invalide, quota depasse, etc. : on degrade
        # proprement plutot que de casser l'experience utilisateur.
        if best_score < MIN_RELEVANT_SCORE:
            return {
                "question": question,
                "answer": phrases["not_found"],
                "sources": [],
                "mode": "aucun_resultat",
                "language": language,
                "fallback_reason": str(e),
            }
        return {
            "question": question,
            "answer": build_extractive_answer(results, language),
            "sources": sources,
            "mode": "extractif",
            "language": language,
            "fallback_reason": str(e),
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate.py \"votre question\"")
        sys.exit(1)
    question = " ".join(sys.argv[1:])

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY non definie. Verification du retrieval seul (sans generation)...\n")
        bm25, documents = load_index()
        results = bm25_query(question, top_k=TOP_K, bm25=bm25, documents=documents)
        print(f"Question : {question}\n")
        print("Extraits qui seraient envoyes a Claude :\n")
        print(build_context_block(results))
        return

    result = answer_question(question)
    print(f"Question : {result['question']}\n")
    print(f"Reponse : {result['answer']}\n")
    print("Sources utilisees :")
    for s in result["sources"]:
        print(f"  - {s['label']} (score BM25: {s['score']})")


if __name__ == "__main__":
    main()
