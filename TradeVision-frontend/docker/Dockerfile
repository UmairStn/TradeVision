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

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Compile TypeScript + build the production Vite bundle
RUN npm run build

# =============================================================
# Stage 3 — Production
#   docker build --target prod -t trade-vision-frontend .
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
