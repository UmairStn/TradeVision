# =============================================================
# Stage 1 — Development
#   docker compose up   (uses the 'dev' target by default)
#   Hot-reload on http://localhost:5173
# =============================================================
FROM node:22-alpine AS dev

WORKDIR /app

# Install dependencies first (layer-cached unless package files change)
COPY package.json package-lock.json ./
RUN npm ci

# Copy the rest of the source code
COPY . .

# Expose Vite's default dev-server port
EXPOSE 5173

# Start the Vite dev server, binding to all interfaces so Docker
# can forward the port to the host machine
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# =============================================================
# Stage 2 — Builder (production bundle)
# =============================================================
FROM node:22-alpine AS builder

WORKDIR /app

# Backend URL for the API client (src/services/api.ts).
#
# This is a BUILD arg, not a runtime env var: Vite inlines import.meta.env at
# compile time, so the value is frozen into the bundle by `npm run build` below.
# Setting it on the running container has no effect. Defaults to localhost:8000,
# which is right when the backend is published on the same machine as the browser.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Compile TypeScript + build the production Vite bundle
RUN npm run build

# =============================================================
# Stage 3 — Production
#   docker build --target prod -t cse-predict-frontend .
#   Serves the compiled bundle via nginx on http://localhost:80
# =============================================================
FROM nginx:1.27-alpine AS prod

# Remove the default nginx welcome page
RUN rm -rf /usr/share/nginx/html/*

# Copy the compiled bundle from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Custom nginx config that supports React Router (SPA fallback)
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
