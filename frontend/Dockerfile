# syntax=docker/dockerfile:1

# --- Stage 1: build the static bundle ---
FROM node:20-slim AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Vite bakes VITE_* env vars into the bundle at BUILD time, not runtime —
# so the backend's public URL has to be known at build time. Railway
# lets you set this as a build-time variable on the frontend service
# (see the deployment guide for the exact steps).
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# --- Stage 2: serve the static bundle with nginx ---
FROM nginx:1.27

COPY --from=build /app/dist /usr/share/nginx/html

# The official nginx image auto-runs envsubst on any *.template file in
# /etc/nginx/templates/ at container startup, writing the result to
# /etc/nginx/conf.d/ — this is what lets $PORT (which Railway sets
# dynamically and differently per deploy) get substituted in without a
# custom entrypoint script.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

ENV PORT=80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
