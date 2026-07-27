"""
Support multilingue pour CustomsRAG (francais / anglais / malgache).

Le corpus source (Code des Douanes, Tarif des Douanes) est entierement en
francais et BM25 est un moteur purement lexical : une question posee en
anglais ou en malgache ne "matche" quasiment aucun token du corpus sans
aide. Ce module fournit :

  1. detect_language() - detection legere (langdetect + heuristique
     malgache, langdetect ne connait pas le malgache nativement)
  2. expand_query() - expansion de la requete avec les equivalents
     francais des termes du glossaire, pour que BM25 retrouve les bons
     documents meme si la question n'est pas en francais
  3. UI_PHRASES - libelles fixes traduits pour le mode extractif (sans LLM)

ATTENTION (transparence) : le glossaire malgache ci-dessous a ete redige
sans locuteur natif pour le valider. Les termes courants (hetra, entana,
fromazy...) sont des emprunts/mots repandus mais le vocabulaire douanier
plus technique peut etre approximatif ou incomplet. A faire valider et
completer par un locuteur avant un usage en production.
"""

import re

from langdetect import detect, LangDetectException

MALAGASY_MARKERS = {
    "ny", "sy", "amin", "ho", "dia", "ary", "amin'ny", "any", "izay",
    "misy", "tsy", "ohatrinona", "inona", "ahoana", "fa", "no", "azo",
    "hetra", "entana", "fadin-tseranana", "sanda", "vidiny",
}


def detect_language(text: str) -> str:
    """Retourne 'fr', 'en' ou 'mg'. Repli sur 'fr' si indetectable."""
    tokens = set(re.findall(r"[a-zà-ÿ']+", text.lower()))
    malagasy_hits = tokens & MALAGASY_MARKERS
    if len(malagasy_hits) >= 2:
        return "mg"

    try:
        detected = detect(text)
    except LangDetectException:
        return "fr"

    if detected == "fr":
        return "fr"
    if detected == "en" and not malagasy_hits:
        return "en"
    if malagasy_hits:
        return "mg"
    return "fr"


# Glossaire d'expansion de requete : terme (EN/MG) -> equivalent(s) FR a
# ajouter a la requete avant la recherche BM25. Volontairement limite au
# vocabulaire douanier/tarifaire le plus frequent plutot qu'un dictionnaire
# general, pour rester precis.
GLOSSARY_EN_TO_FR = {
    "customs": "douane douanier", "duty": "droit de douane", "duties": "droits de douane",
    "rate": "taux", "tax": "taxe impot", "vat": "tva", "code": "code",
    "cheese": "fromage", "honey": "miel natural", "eggs": "oeufs", "egg": "oeuf",
    "horse": "cheval chevaux", "fraud": "fraude", "penalty": "sanction",
    "penalties": "sanctions", "import": "importer importation",
    "export": "exporter exportation", "goods": "marchandises",
    "declaration": "declaration", "warehouse": "entrepot",
    "exemption": "exemption exonere", "law": "loi", "regulation": "reglement",
    "article": "article", "chapter": "chapitre", "weight": "poids",
    "value": "valeur", "invoice": "facture", "certificate": "certificat",
    "origin": "origine",
}

GLOSSARY_MG_TO_FR = {
    "hetra": "taxe impot droit de douane",
    "fadin-tseranana": "douane",
    "entana": "marchandise",
    "vidiny": "valeur prix",
    "sanda": "poids",
    "fromazy": "fromage",
    "tantely": "miel",
    "atody": "oeufs",
    "soavaly": "cheval",
    "sazy": "sanction penalite",
    "hosoka": "fraude faux",
    "lalàna": "loi",
    "fitsipika": "reglement",
    "andininy": "article",
    "toko": "chapitre",
}


def expand_query(question: str, language: str) -> str:
    """Traduit les mots-cles reconnus vers le francais, pour aider BM25
    sans avoir besoin d'un appel LLM de traduction (gratuit, hors-ligne).

    Pour une question non francaise, on ne recherche QUE la traduction
    (pas le texte original) : les mots anglais/malgaches ne matchent de
    toute facon rien dans le corpus francais, sauf par coincidence sur une
    expression etrangere citee telle quelle dans un texte (ex: "duty free
    shop" dans le Code des Douanes), ce qui fausserait le classement."""
    if language == "fr":
        return question

    glossary = GLOSSARY_EN_TO_FR if language == "en" else GLOSSARY_MG_TO_FR
    words = re.findall(r"[a-zà-ÿ'\-]+", question.lower())
    additions = [glossary[w] for w in words if w in glossary]

    if not additions:
        return question  # rien reconnu : on tente quand meme avec l'original
    return " ".join(additions)


# Libelles fixes pour le mode extractif (sans generation LLM), ou l'on ne
# peut pas traduire le contenu regulatoire lui-meme (il reste en francais,
# langue de reference legale) mais on peut au moins traduire l'habillage.
UI_PHRASES = {
    "fr": {
        "extractive_header": "[Mode extractif - sans generation IA]",
        "according_to": "D'apres",
        "other_extracts": "Autres extraits potentiellement pertinents :",
        "source_note": "(texte source en francais, langue de reference legale)",
        "not_found": "Je ne trouve pas cette information dans les extraits disponibles.",
    },
    "en": {
        "extractive_header": "[Extractive mode - no AI generation]",
        "according_to": "According to",
        "other_extracts": "Other potentially relevant extracts:",
        "source_note": "(source text in French, the legal reference language)",
        "not_found": "This information could not be found in the available extracts.",
    },
    "mg": {
        "extractive_header": "[Fomba fanalana - tsy misy famoronana AI]",
        "according_to": "Araka ny",
        "other_extracts": "Sombiny hafa mety ho ilaina:",
        "source_note": "(soratra loharano amin'ny teny frantsay, fiteny ara-dalàna)",
        "not_found": "Tsy hita ao anatin'ny sombiny misy ity fampahalalana ity.",
    },
}
