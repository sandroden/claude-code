# syntax=docker/dockerfile:experimental

# develop stage
FROM oven/bun:1.1-alpine AS develop-stage
WORKDIR /app

# Copia file di dipendenze
COPY package.json bun.lockb ./

# Installa Quasar CLI globalmente
RUN bun add -g @quasar/cli

# Copia il resto del progetto
COPY . .

# build stage
FROM develop-stage AS build-stage
RUN bun install --frozen-lockfile
RUN bun run build

# production stage
FROM nginx:1.29.0-alpine AS production-stage

# Copia build Quasar
COPY --from=build-stage /app/dist/spa /usr/share/nginx/html

# Configurazione nginx
COPY --from=build-stage /app/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
