# Frontend CustomsRAG - build React/TS puis service via Nginx
FROM node:20-slim AS build

WORKDIR /app
COPY package.json package-lock.json* ./
# strict-ssl=false : meme contournement que cote backend, pour les
# reseaux/antivirus qui interceptent le HTTPS avec leur propre certificat.
RUN npm config set strict-ssl false && npm ci

COPY . .
RUN npm run build

# --- Etape finale : serveur statique leger ---
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
