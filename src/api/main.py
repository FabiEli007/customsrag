"""
API FastAPI pour CustomsRAG.

Endpoints :
  GET  /health        - etat du service (index charge, cle API presente)
  POST /ask           - question -> reponse + sources citees
  GET  /sources/stats - statistiques sur le corpus indexe (utile pour un dashboard)

Lancement local :
  export ANTHROPIC_API_KEY="sk-ant-..."
  uvicorn src.api.main:app --reload --port 8000
"""

import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.retrieval.bm25_index import load_index
from src.rag.generate import answer_question, MODEL

# Etat partage, charge une seule fois au demarrage (pas a chaque requete)
state: dict = {"bm25": None, "documents": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Chargement de l'index BM25...")
    state["bm25"], state["documents"] = load_index()
    print(f"Index charge : {len(state['documents'])} documents")
    yield
    state.clear()


app = FastAPI(
    title="CustomsRAG API",
    description="Assistant IA pour la reglementation douaniere et tarifaire de Madagascar",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # a restreindre en production
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=15)


class SourceRef(BaseModel):
    label: str
    score: float


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceRef]
    latency_ms: int
    mode: str  # "generatif" | "extractif" | "aucun_resultat"
    language: str  # "fr" | "en" | "mg"


class HealthResponse(BaseModel):
    status: str
    index_loaded: bool
    documents_count: int
    api_key_configured: bool
    model: str


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok" if state["bm25"] is not None else "index_not_loaded",
        index_loaded=state["bm25"] is not None,
        documents_count=len(state["documents"]) if state["documents"] else 0,
        api_key_configured=bool(os.environ.get("ANTHROPIC_API_KEY")),
        model=MODEL,
    )


@app.get("/sources/stats")
def sources_stats():
    if not state["documents"]:
        raise HTTPException(status_code=503, detail="Index non charge")
    counts: dict[str, int] = {}
    for d in state["documents"]:
        counts[d["source_type"]] = counts.get(d["source_type"], 0) + 1
    return {"total": len(state["documents"]), "par_source": counts}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    if state["bm25"] is None:
        raise HTTPException(status_code=503, detail="Index non charge, reessayez dans un instant.")

    start = time.perf_counter()
    result = answer_question(req.question, top_k=req.top_k)

    return AskResponse(
        question=result["question"],
        answer=result["answer"],
        sources=[SourceRef(**s) for s in result["sources"]],
        latency_ms=int((time.perf_counter() - start) * 1000),
        mode=result["mode"],
        language=result["language"],
    )
