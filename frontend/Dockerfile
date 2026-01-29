# Stage 1: build the app
FROM node:18-alpine AS builder

WORKDIR /app

# Install dependencies (use package-lock if present)
COPY package*.json ./
RUN npm ci --silent

# Copy source and build
COPY . .
RUN npm run build

# Stage 2: serve with nginx
FROM nginx:stable-alpine

# Remove default nginx config and add our own
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 3000

# Simple healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
