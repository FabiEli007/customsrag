"""
Ingestion du Tarif des Douanes de Madagascar (edition Janvier 2025, base SH 2022).

Document a une seule colonne (pas de probleme de mise en page comme le
Code des Douanes) mais son contenu est un tableau tarifaire avec des lignes
qui peuvent s'etaler sur plusieurs lignes physiques : le code SH et le
debut de la designation apparaissent d'abord, puis eventuellement une ou
plusieurs lignes de continuation, et enfin l'unite + les taux (DD, TVA,
DD APEi) tout a la fin du bloc.

Strategie : extraction texte via pdftotext -layout (les colonnes du tableau
restent correctement alignees en mode "layout" pour ce document, contrairement
au Code des Douanes qui est en 2 colonnes de texte).
On parcourt ensuite le texte ligne par ligne avec une petite machine a etats
qui distingue :
  - les positions SH a 4 chiffres ("04.06") = simples intitules de groupe,
    sans taux propres ;
  - les codes SH complets ("0406.10 00") = lignes tarifaires avec taux ;
  - les en-tetes de Chapitre / Section ;
  - les blocs de "Notes" / "Notes explicatives" (texte libre rattache au
    chapitre courant, conserve comme chunk a part).
"""

import json
import re
import subprocess
from pathlib import Path

PDF_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "TARIF-DES-DOUANES-2025.pdf"
OUT_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "tarif_douanes_chunks.json"

# Le sommaire (pages 1-6 environ) liste tous les chapitres a l'avance ; le
# tableau tarifaire proprement dit commence apres. Detecte dynamiquement
# via la premiere ligne "Chapitre 1" suivie de vrais codes SH.
MIN_CONTENT_PAGE = 7

FULL_CODE_RE = re.compile(r"^(\d{4}\.\d{2}\s?\d{2})\s+(.*)$")
SUBHEADING_CODE_RE = re.compile(r"^(\d{4}\.\d{2})\s+(.*)$")
HEADING_CODE_RE = re.compile(r"^(\d{2}\.\d{2})\s+(.*)$")
CHAPITRE_RE = re.compile(r"^\s*Chapitre\s+(\d+)\b\s*(.*)$", re.IGNORECASE)
SECTION_RE = re.compile(r"^\s*SECTION[\s.\-]*([IVXLCDM]+)\s*(.*)$", re.IGNORECASE)
NOTES_START_RE = re.compile(r"^\s*Notes?(\s+explicatives?)?\.?\s*$", re.IGNORECASE)

# Lignes de bruit recurrentes : en-tete de tableau reimprime a chaque page,
# separateurs de section (traits de soulignement), colonne "DD" isolee
# au-dessus de "DD APEi".
NOISE_RE = re.compile(
    r"^\s*(TARIF\s*N|DESIGNATION\s+DES\s+PRODUITS|UQN\s+DD\s+TVA|DD\s*$|_{4,}\s*)",
    re.IGNORECASE,
)

# Fin de bloc = unite (optionnelle) + 3 valeurs de taux (nombre ou "ex"),
# suivi eventuellement d'une 4e colonne "Droit Specifique" (ex: chapitre 25
# des mineraux, colonne supplementaire "Valeur ex").
END_RATES_RE = re.compile(
    r"(?P<unit>[A-Za-zÀ-ÿ²]{1,6})?\s{2,}(?P<dd>\d+(?:[.,]\d+)?|ex)\s+"
    r"(?P<tva>\d+(?:[.,]\d+)?|ex)\s+(?P<apei>\d+(?:[.,]\d+)?|ex)"
    r"(?:\s+Valeur\s+(?P<ds>\d+(?:[.,]\d+)?|ex))?"
    r"\s*$",
    re.IGNORECASE,
)

FOOTER_RE = re.compile(r"^\s*\d+\s*(Tarif\s*20\d\d)?\s*$")
DASH_FILL_RE = re.compile(r"-{4,}")


def extract_page_lines():
    """Retourne une liste de (page_num, [lignes]) via pdftotext -layout."""
    proc = subprocess.run(
        ["pdftotext", "-layout", str(PDF_PATH), "-"],
        capture_output=True, text=True, check=True,
    )
    pages = proc.stdout.split("\f")
    result = []
    for i, page_text in enumerate(pages):
        result.append((i + 1, page_text.split("\n")))
    return result


def clean_designation(text: str) -> str:
    text = DASH_FILL_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip(" -")
    return text.strip()


def _rates_complete(lines) -> bool:
    """True si le texte accumule se termine deja par un bloc de taux complet
    (permet un flush immediat avant qu'une ligne de bruit suivante ne vienne
    se coller a la fin, ex: un intitule '- Buffles :' sans code propre)."""
    joined = " ".join(lines)
    m = END_RATES_RE.search(joined)
    return bool(m and m.end() == len(joined))


def parse_tarif():
    pages = extract_page_lines()
    chunks = []

    current_chapitre_num = None
    current_chapitre_title = None
    current_section = None
    current_heading = None      # position SH 4 chiffres (ex: "01.01 Chevaux...")
    current_subheading = None   # sous-position 6 chiffres, sans taux (ex: "0104.20 - De l'espece caprine")
    awaiting_chapitre_title = False

    pending_code = None
    pending_lines = []
    pending_page_start = None

    notes_buffer = []
    notes_page_start = None

    def flush_notes():
        nonlocal notes_buffer, notes_page_start
        if notes_buffer:
            text = clean_designation(" ".join(notes_buffer))
            if len(text) > 10:
                chunks.append({
                    "source": "TARIF-DES-DOUANES-2025.pdf",
                    "type": "note_explicative",
                    "chapitre": current_chapitre_num,
                    "chapitre_titre": current_chapitre_title,
                    "section": current_section,
                    "position_sh": current_heading,
                    "page": notes_page_start,
                    "text": text,
                })
        notes_buffer = []
        notes_page_start = None

    def flush_pending():
        nonlocal pending_code, pending_lines, pending_page_start
        if pending_code is None:
            return
        joined = " ".join(pending_lines)
        m = END_RATES_RE.search(joined)
        if m:
            designation = clean_designation(joined[: m.start()])
            chunks.append({
                "source": "TARIF-DES-DOUANES-2025.pdf",
                "type": "ligne_tarifaire",
                "code_sh": pending_code,
                "designation": designation,
                "position_sh": current_heading,
                "sous_position_sh": current_subheading,
                "chapitre": current_chapitre_num,
                "chapitre_titre": current_chapitre_title,
                "section": current_section,
                "unite": (m.group("unit") or "").strip() or None,
                "dd": m.group("dd"),
                "tva": m.group("tva"),
                "dd_apei": m.group("apei"),
                "droit_specifique": m.group("ds"),
                "page": pending_page_start,
                "text": (
                    f"Code SH {pending_code} - {designation}. "
                    f"Droit de douane (DD): {m.group('dd')}. "
                    f"TVA: {m.group('tva')}. DD APEi: {m.group('apei')}."
                    + (f" Unite: {(m.group('unit') or '').strip()}." if m.group("unit") else "")
                    + (f" Droit specifique (sur valeur): {m.group('ds')}." if m.group("ds") else "")
                ),
            })
        else:
            # Pas de taux trouve (rare: ligne tronquee / cas particulier) :
            # on garde quand meme la designation en texte pour ne rien perdre.
            designation = clean_designation(joined)
            if designation:
                chunks.append({
                    "source": "TARIF-DES-DOUANES-2025.pdf",
                    "type": "ligne_tarifaire_incomplete",
                    "code_sh": pending_code,
                    "designation": designation,
                    "position_sh": current_heading,
                    "chapitre": current_chapitre_num,
                    "chapitre_titre": current_chapitre_title,
                    "section": current_section,
                    "page": pending_page_start,
                    "text": f"Code SH {pending_code} - {designation}.",
                })
        pending_code = None
        pending_lines = []
        pending_page_start = None

    in_notes = False

    for page_num, lines in pages:
        if page_num < MIN_CONTENT_PAGE:
            continue
        for raw_line in lines:
            line = raw_line.rstrip()
            if not line.strip() or FOOTER_RE.match(line) or NOISE_RE.match(line):
                continue

            chap_m = CHAPITRE_RE.match(line)
            if chap_m:
                flush_pending()
                flush_notes()
                in_notes = False
                current_chapitre_num = chap_m.group(1)
                inline_title = chap_m.group(2).strip()
                current_chapitre_title = inline_title or None
                awaiting_chapitre_title = not bool(inline_title)
                current_heading = None
                current_subheading = None
                continue

            if awaiting_chapitre_title:
                # La 1ere ligne non-vide suivant "Chapitre N" seule est le
                # titre du chapitre (ex: "Animaux vivants").
                current_chapitre_title = line.strip()
                awaiting_chapitre_title = False
                continue

            sec_m = SECTION_RE.match(line)
            if sec_m:
                flush_pending()
                flush_notes()
                in_notes = False
                current_section = f"SECTION {sec_m.group(1)} {sec_m.group(2)}".strip()
                continue

            if NOTES_START_RE.match(line):
                flush_pending()
                in_notes = True
                notes_page_start = page_num
                notes_buffer = [line.strip()]
                continue

            full_m = FULL_CODE_RE.match(line)
            sub_m = None if full_m else SUBHEADING_CODE_RE.match(line)
            heading_m = None if (full_m or sub_m) else HEADING_CODE_RE.match(line)

            if full_m:
                flush_pending()
                flush_notes()
                in_notes = False
                pending_code = full_m.group(1)
                pending_lines = [full_m.group(2)]
                pending_page_start = page_num
                if _rates_complete(pending_lines):
                    flush_pending()
                continue

            if sub_m:
                flush_pending()
                flush_notes()
                in_notes = False
                current_subheading = f"{sub_m.group(1)} {clean_designation(sub_m.group(2))}".strip()
                continue

            if heading_m:
                flush_pending()
                flush_notes()
                in_notes = False
                current_heading = f"{heading_m.group(1)} {clean_designation(heading_m.group(2))}".strip()
                current_subheading = None
                continue

            if pending_code is not None:
                pending_lines.append(line.strip())
                if _rates_complete(pending_lines):
                    flush_pending()
            elif in_notes:
                notes_buffer.append(line.strip())
            # sinon : continuation de sous-titre ou bruit residuel -> ignoree

    flush_pending()
    flush_notes()
    return chunks


def main():
    print(f"Lecture de {PDF_PATH.name} ...")
    chunks = parse_tarif()
    print(f"{len(chunks)} chunks extraits")

    by_type = {}
    for c in chunks:
        by_type[c["type"]] = by_type.get(c["type"], 0) + 1
    print("Repartition par type:", by_type)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"Ecrit dans {OUT_PATH}")

    print("\n--- Apercu ---")
    for c in [x for x in chunks if x["type"] == "ligne_tarifaire"][:5]:
        print(c["text"], "|", c["chapitre_titre"], "|", c["position_sh"])


if __name__ == "__main__":
    main()
