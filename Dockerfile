# Backend CustomsRAG - API FastAPI (retrieval BM25 + generation Claude)
FROM python:3.12-slim

WORKDIR /app

# Dependances Python d'abord (couche cachee separement du code source,
# pour que les rebuilds lors de changements de code ne reinstallent pas
# tout a chaque fois).
COPY requirements.txt .
# --trusted-host : contourne les antivirus/proxy qui interceptent le
# trafic HTTPS avec leur propre certificat (frequent sur reseaux
# d'entreprise ou avec certains antivirus). A retirer si votre reseau
# n'a pas ce probleme.
RUN pip install --no-cache-dir \
    --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pythonhosted.org \
    -r requirements.txt

# Code source + donnees pre-traitees (chunks JSON + index BM25 deja
# construits - pas besoin de re-parser les PDF au demarrage du conteneur).
COPY src ./src
COPY data/processed ./data/processed
COPY data/vector_store ./data/vector_store

# ANTHROPIC_API_KEY est injectee a l'execution (docker run -e ... ou
# docker-compose.yml), jamais copiee dans l'image.
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
