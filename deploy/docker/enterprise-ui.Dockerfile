# ============================================================
# PromptShield Enterprise UI - Multi-stage Docker build
# ============================================================

# --- Stage 1: Node build ---
FROM node:20-alpine AS builder

WORKDIR /app

COPY apps/promptshield-enterprise-ui/package.json ./
COPY apps/promptshield-enterprise-ui/package-lock.json* ./

RUN npm ci --frozen-lockfile

COPY apps/promptshield-enterprise-ui/ .

# Build args for API URL (baked into the bundle at build time)
ARG VITE_API_BASE_URL=http://localhost:8000/api
ARG VITE_API_KEY=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_API_KEY=$VITE_API_KEY

RUN npm run build

# --- Stage 2: nginx serve ---
FROM nginx:1.27-alpine AS runtime

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Add custom nginx config for SPA routing
COPY deploy/docker/nginx-ui.conf /etc/nginx/conf.d/default.conf

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
