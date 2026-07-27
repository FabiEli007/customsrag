"""
Ingestion du Code des Douanes (Madagascar, apres LFI 2026).

Le PDF est mis en page sur 2 colonnes. pdftotext -layout melange les deux
colonnes ligne par ligne (texte incoherent). On extrait donc chaque page
avec pdfplumber en la decoupant en deux moities (gauche/droite), puis on
concatene colonne gauche -> colonne droite -> page suivante, ce qui restitue
l'ordre de lecture naturel.

Une fois le texte reconstruit, on decoupe en chunks au niveau de l'article
de loi (unite juridique naturelle), en accrochant a chaque chunk ses
metadonnees hierarchiques (Titre / Chapitre / Section) et les references
de loi de modification trouvees dans le texte.
"""

import json
import re
from pathlib import Path

import pdfplumber

PDF_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "CODE-DES-DOUANES-APRES-LFI-2026.pdf"
OUT_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "code_douanes_chunks.json"

PAGE_MARKER = "\u27e6PAGE:{}\u27e7"  # ⟦PAGE:15⟧ - unlikely to appear in real text

# Repere le debut de la partie operative (apres page de garde + sommaire).
# Le sommaire est detecte automatiquement (voir find_content_start), ce
# numero sert seulement de garde-fou.
MIN_CONTENT_PAGE = 12

# Le Code utilise des suffixes latins d'ordinaux qui vont bien au-dela de
# "Sexies" pour les articles ajoutes par amendements successifs (ex: zone
# franche, Art. 229 Bis a Art. 229 Septvicies = 27 sous-articles). On
# capture donc un mot-suffixe generique plutot qu'une liste fermee, avec
# une eventuelle annotation "(nouveau)" avant la ponctuation terminale.
ARTICLE_PATTERN = re.compile(
    r"(Article\s+premier|Art\.?\s*\d+[a-zA-Z]*(?:\s+[A-Za-zÀ-ÿ]+)?)"
    r"\s*(?:\([^)]{0,20}\))?\s*[\.\-\u2013]",
)

_NUM = r"(?:PREMIER|[IVXLCDM]+)"
TITRE_PATTERN = re.compile(rf"^TITRE\s+{_NUM}(?:\s*BIS)?\b.*", re.MULTILINE)
CHAPITRE_PATTERN = re.compile(rf"^CHAPITRE\s+{_NUM}(?:\s+Bis)?\s*:?.*", re.MULTILINE)
SECTION_PATTERN = re.compile(rf"^Section\s+{_NUM}\s*[\.\-–].*", re.MULTILINE)

LOI_REF_PATTERN = re.compile(
    r"\((?:Loi|Ordonnance)\s+n[°ø]\s?[\d\-A-Za-z]+\s+du\s+[\d./]+\s+portant\s+[^\)]+\)"
)


def extract_page_text(page) -> str:
    """Extrait le texte d'une page en respectant l'ordre 2-colonnes."""
    width, height = page.width, page.height
    left = page.crop((0, 0, width / 2, height))
    right = page.crop((width / 2, 0, width, height))
    left_text = left.extract_text() or ""
    right_text = right.extract_text() or ""

    # Certaines pages (couverture, annexes) ne sont pas en 2 colonnes :
    # si un cote est vide/quasi vide, on retombe sur le texte pleine page.
    if len(left_text.strip()) < 20 or len(right_text.strip()) < 20:
        full = page.extract_text() or ""
        return full
    return left_text + "\n" + right_text


def build_full_text() -> str:
    parts = []
    with pdfplumber.open(PDF_PATH) as pdf:
        for i, page in enumerate(pdf.pages):
            page_num = i + 1
            text = extract_page_text(page)
            parts.append(PAGE_MARKER.format(page_num))
            parts.append(text)
    return "\n".join(parts)


def strip_page_markers_get_page(pos_text: str) -> int:
    """Retourne le dernier numero de page rencontre avant la position donnee."""
    matches = list(re.finditer(r"\u27e6PAGE:(\d+)\u27e7", pos_text))
    if not matches:
        return 0
    return int(matches[-1].group(1))


def find_content_start(full_text: str) -> int:
    """Localise le debut du texte operatif (le premier 'Article premier'),
    en ignorant les occurrences trouvees dans le sommaire (avant page 12)."""
    for m in ARTICLE_PATTERN.finditer(full_text):
        page = strip_page_markers_get_page(full_text[: m.start()])
        if page >= MIN_CONTENT_PAGE and "premier" in m.group(1).lower():
            return m.start()
    return 0


def parse_articles(full_text: str):
    start = find_content_start(full_text)
    body = full_text[start:]

    matches = list(ARTICLE_PATTERN.finditer(body))
    chunks = []

    # Seed les en-tetes hierarchiques avec tout ce qui precede le premier
    # article (le "Chapitre premier" apparait juste avant "Article premier"
    # dans l'expose des motifs).
    preamble = full_text[:start]
    # Le sommaire (pages ~2-13) contient TOUS les intitules de chapitres a
    # l'avance : ne pas s'en servir pour le seed, sinon on capte le dernier
    # chapitre liste dans le sommaire au lieu de celui qui precede vraiment
    # le premier article. On ne garde donc que le texte a partir de la
    # derniere page anterieure a MIN_CONTENT_PAGE.
    page_markers_before = list(re.finditer(r"\u27e6PAGE:(\d+)\u27e7", preamble))
    cut_at = 0
    for pm in page_markers_before:
        if int(pm.group(1)) >= MIN_CONTENT_PAGE - 1:
            cut_at = pm.start()
            break
    preamble = preamble[cut_at:]
    current_titre = None
    current_chapitre = None
    current_section = None
    for tm in TITRE_PATTERN.finditer(preamble):
        current_titre = re.sub(r"\s+", " ", tm.group(0)).strip()
    for cm in CHAPITRE_PATTERN.finditer(preamble):
        current_chapitre = re.sub(r"\s+", " ", cm.group(0)).strip()
    for sm in SECTION_PATTERN.finditer(preamble):
        current_section = re.sub(r"\s+", " ", sm.group(0)).strip()

    cursor = 0

    for idx, m in enumerate(matches):
        chunk_start = m.start()
        chunk_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)

        # Texte entre l'article precedent et celui-ci : sert a mettre a jour
        # les en-tetes hierarchiques (Titre / Chapitre / Section) rencontres
        # en cours de route (ils apparaissent souvent en fin de colonne,
        # juste avant le prochain article).
        between = body[cursor:chunk_start]
        for tm in TITRE_PATTERN.finditer(between):
            current_titre = re.sub(r"\s+", " ", tm.group(0)).strip()
        for cm in CHAPITRE_PATTERN.finditer(between):
            current_chapitre = re.sub(r"\s+", " ", cm.group(0)).strip()
        for sm in SECTION_PATTERN.finditer(between):
            current_section = re.sub(r"\s+", " ", sm.group(0)).strip()

        raw_chunk = body[chunk_start:chunk_end]
        page_num = strip_page_markers_get_page(full_text[: start + chunk_start])

        # Nettoyage : retire les marqueurs de page internes au chunk (un
        # article peut chevaucher 2 pages), garde une liste de pages couvertes.
        pages_covered = sorted(set(
            int(p) for p in re.findall(r"\u27e6PAGE:(\d+)\u27e7", raw_chunk)
        )) or [page_num]
        clean_text = re.sub(r"\u27e6PAGE:\d+\u27e7", "", raw_chunk)
        clean_text = re.sub(r"[ \t]+", " ", clean_text)
        clean_text = re.sub(r"\n{3,}", "\n\n", clean_text).strip()

        article_label = re.sub(r"\s+", " ", m.group(1)).strip()
        references_loi = LOI_REF_PATTERN.findall(clean_text)

        chunks.append({
            "source": "CODE-DES-DOUANES-APRES-LFI-2026.pdf",
            "article": article_label,
            "titre": current_titre,
            "chapitre": current_chapitre,
            "section": current_section,
            "pages": pages_covered,
            "references_loi": references_loi,
            "text": clean_text,
            "n_chars": len(clean_text),
        })
        cursor = chunk_start

    return chunks


def main():
    print(f"Lecture de {PDF_PATH.name} ...")
    full_text = build_full_text()
    print(f"Texte extrait : {len(full_text)} caracteres")

    chunks = parse_articles(full_text)
    print(f"{len(chunks)} chunks (articles) extraits")

    # Filtre les chunks quasi-vides ou aberrants (faux positifs de regex)
    chunks = [c for c in chunks if c["n_chars"] >= 15]
    print(f"{len(chunks)} chunks apres filtrage")

    # Deduplique les chunks au contenu strictement identique (meme article,
    # meme texte). Cause typique : chevauchement d'extraction sur une
    # frontiere de page (colonne recapturee deux fois). On garde la
    # premiere occurrence. Ne touche pas aux cas legitimes ou un meme
    # numero d'article porte plusieurs alineas distincts (amendements
    # successifs), qui ont un texte different.
    seen = set()
    deduped = []
    n_removed = 0
    for c in chunks:
        key = (c["article"], c["text"])
        if key in seen:
            n_removed += 1
            continue
        seen.add(key)
        deduped.append(c)
    chunks = deduped
    if n_removed:
        print(f"{n_removed} doublons de texte exact supprimes")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"Ecrit dans {OUT_PATH}")

    # Apercu
    for c in chunks[:3]:
        print("\n---")
        print(f"Article: {c['article']} | Chapitre: {c['chapitre']} | Pages: {c['pages']}")
        print(c["text"][:200])


if __name__ == "__main__":
    main()
