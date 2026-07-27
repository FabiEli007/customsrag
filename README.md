# CustomsRAG

**Assistant IA (RAG) pour la réglementation douanière et tarifaire de Madagascar**

Un assistant conversationnel qui répond aux questions sur le Code des Douanes et le Tarif des Douanes de Madagascar, en citant systématiquement l'article de loi ou le code SH exact utilisé — en français, en anglais ou en malgache.

Projet réalisé pour démontrer les compétences LLM / RAG / industrialisation demandées pour un poste de **Data Scientist IA Junior** (SGS Madagascar).

---

## Pourquoi ce projet

Le Code des Douanes et le Tarif des Douanes malgaches totalisent plus de 390 pages de texte réglementaire dense. Y retrouver rapidement un taux de droit de douane, un code SH ou une disposition légale précise est fastidieux — CustomsRAG transforme ces deux documents en base de connaissance interrogeable en langage naturel, avec traçabilité complète de la source.

## Aperçu

> *(ajouter ici une capture d'écran ou un GIF de démo — `docs/screenshot.png`)*

**Exemple de question :** *"Quel est le taux de droit de douane pour le fromage ?"*
**Réponse :** citation directe du code SH 0406.10 00 (Tarif des Douanes) avec les taux DD/TVA/DD APEi, sourcée et affichée dans le "Registre des sources".

**Exemple hors périmètre :** *"Quel est le taux de TVA en France ?"*
**Réponse :** *"Je ne trouve pas cette information dans les extraits disponibles."* — le système ne devine jamais, il refuse honnêtement plutôt que d'halluciner.

---

## Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌────────────────────┐
│   PDF sources    │      │   Ingestion       │      │  Index BM25         │
│  Code des        │─────▶│  (pdfplumber,     │─────▶│  (rank_bm25,        │
│  Douanes,        │      │  parsing 2-col +  │      │  5 387 chunks,      │
│  Tarif 2025      │      │  tableau tarifaire)│      │  detection FR/EN/MG)│
└─────────────────┘      └──────────────────┘      └──────────┬─────────┘
                                                                │
┌─────────────────┐      ┌──────────────────┐      ┌──────────▼─────────┐
│  Frontend        │◀────▶│  API FastAPI      │◀────│  RAG (retrieval +   │
│  React + TS      │      │  /ask /health     │      │  generation Claude, │
│  Tailwind         │      │  /sources/stats   │      │  fallback extractif)│
└─────────────────┘      └──────────────────┘      └────────────────────┘
```

## Stack technique

| Composant | Choix | Justification |
|---|---|---|
| Ingestion PDF | `pdfplumber` | Extraction colonne par colonne pour gérer la mise en page à 2 colonnes du Code des Douanes |
| Retrieval | `rank_bm25` (BM25 Okapi) | Excellent sur le vocabulaire exact (codes SH, numéros d'article) ; ne nécessite aucun téléchargement de modèle |
| Génération | Claude Haiku (`claude-haiku-4-5`) via API Anthropic | Rapide et économique — le gros du travail est fait par le retrieval, pas par le raisonnement |
| Backend | FastAPI | Endpoints typés (Pydantic), CORS, gestion d'erreurs propre |
| Frontend | React + TypeScript + Tailwind CSS | Typage strict, build de production optimisé |
| Multilingue | `langdetect` + glossaire métier | Détection FR/EN/MG, expansion de requête pour le malgache/anglais |

## Fonctionnalités

- **Réponses sourcées** : chaque réponse cite l'article du Code des Douanes ou le code SH du Tarif utilisé — jamais de réponse sans référence vérifiable
- **Refus honnête** : si l'information n'est pas dans le corpus, le système le dit clairement plutôt que d'inventer (seuil de pertinence calibré sur le score BM25)
- **Multilingue** : questions en français, anglais ou malgache ; l'interface aussi
- **Mode dégradé (« extractif »)** : si l'API Claude est indisponible (pas de crédit, quota dépassé), le système continue de fonctionner en renvoyant directement l'extrait le plus pertinent plutôt que de tomber en erreur
- **Registre des sources** : panneau qui recense en temps réel tous les articles/codes SH consultés au fil de la conversation

## Défis techniques résolus

Quelques problèmes réels rencontrés pendant le développement (au-delà du "hello world RAG") :

- **Mise en page à 2 colonnes** du Code des Douanes : `pdftotext -layout` mélangeait les colonnes ligne par ligne. Résolu par extraction `pdfplumber` avec découpage gauche/droite par page.
- **Suffixes latins d'articles non standards** (`Art. 229 Septvicies`) : le Code va bien au-delà de "Bis/Ter/Quater" habituels (jusqu'à 27 amendements sur un seul article numéroté), nécessitant un parsing générique plutôt qu'une liste fermée de suffixes.
- **Hiérarchie à 3 niveaux** dans le Tarif des Douanes : position 4 chiffres → sous-position 6 chiffres (sans taux propre) → ligne tarifaire complète 8 chiffres, avec un flush "eager" pour éviter que des intitulés de catégorie sans code ne se collent aux lignes tarifaires voisines.
- **Ligature "œ"** : `unicodedata.normalize` ne décompose pas les ligatures (contrairement aux accents), ce qui cassait silencieusement la recherche sur tous les termes contenant "œ" (ex: "œufs" tokenisé en "ufs").
- **Faux positifs de pertinence** : sans seuil de score minimum, une question hors périmètre ("TVA en France") remontait un article sans rapport avec un score BM25 non nul. Un seuil calibré empiriquement évite de présenter un extrait non pertinent comme une réponse valide.

## Installation

```bash
git clone <ce-repo>
cd CustomsRAG
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

## Lancement

**Backend** (terminal 1, depuis la racine du projet) :
```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # optionnel : sans cle, mode extractif automatique
uvicorn src.api.main:app --port 8000
```

**Frontend** (terminal 2) :
```bash
cd frontend
npm run dev
```

Puis ouvrir `http://localhost:5173`.

## Reconstruire l'index depuis les PDF sources

```bash
python3 src/ingestion/parse_code_douanes.py
python3 src/ingestion/parse_tarif_douanes.py
python3 src/retrieval/bm25_index.py
```

## Limites connues

Transparence plutôt que promesses excessives :

- **Chapitre 27 (produits pétroliers)** du Tarif utilise une notation de taux différente (`213*`, `20%`, unités Ariary/litre avec renvois de notes) — 40 lignes sur 4 821 (< 1%) ne sont pas parsées, documentées comme telles plutôt que masquées.
- **Glossaire malgache** : point de départ volontairement modeste (vocabulaire douanier de base sourcé), à enrichir par un locuteur natif pour une couverture complète du vocabulaire des marchandises.
- **BM25 plutôt qu'embeddings denses** : choix pragmatique (pas de dépendance à un téléchargement de modèle HuggingFace), au prix d'une compréhension purement lexicale plutôt que sémantique. Une évolution naturelle serait un retrieval hybride BM25 + embeddings.

## Lancement avec Docker (recommandé pour une démo reproductible)

```bash
cp .env.example .env
# renseigner ANTHROPIC_API_KEY dans .env (optionnel : sans cle, mode extractif automatique)

docker compose up --build
```

- Frontend : http://localhost:8080
- Backend (API directe) : http://localhost:8000/docs

Le frontend (Nginx) sert les fichiers statiques compilés et reverse-proxy `/api/*` vers le conteneur backend — pas de configuration CORS ni de port à gérer manuellement.

## Intégration continue

Un workflow GitHub Actions (`.github/workflows/ci.yml`) exécute automatiquement à chaque push :
- les 20 tests pytest (ingestion, retrieval, pipeline RAG, API)
- la vérification TypeScript + build de production du frontend

## Roadmap

- [x] Dockerisation (backend + frontend)
- [x] Tests automatisés (pytest) + CI GitHub Actions
- [ ] Retrieval hybride (BM25 + embeddings denses)
- [ ] Enrichissement du glossaire malgache par un locuteur natif

## Auteur

RANDRIAKAMAMY Fabien Elyote — [GitHub @FabiEli007](https://github.com/FabiEli007)
