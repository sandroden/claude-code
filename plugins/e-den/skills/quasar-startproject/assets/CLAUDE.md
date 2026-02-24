# Progetto Quasar (Frontend) — Mode: __MODE__

## Package manager

Questo progetto usa **bun** come package manager.

- Aggiungere dipendenze: `bun add <package>`
- Aggiungere dipendenze dev: `bun add --dev <package>`
- Eseguire dev server: `bun run dev`
- Build produzione: `bun run build`

## Stack

- **Vue 3** con Composition API (`<script setup>`)
- **TypeScript**
- **Quasar v2** (framework UI) — mode: **__MODE__**
- **Pinia** per state management
- **Vite** come build tool
- **SCSS** come preprocessore CSS

## Proxy verso Django

Il dev server (`quasar.config.ts`) ha un proxy configurato verso `http://localhost:8000` per:
- `/api` — API backend
- `/admin` — Django admin
- `/static` — File statici Django
- `/media` — File media Django

Assicurarsi che il backend Django sia in esecuzione sulla porta 8000.

## Struttura

- `src/pages/` — Pagine dell'applicazione
- `src/components/` — Componenti riutilizzabili
- `src/layouts/` — Layout dell'applicazione
- `src/stores/` — Store Pinia
- `src/router/` — Configurazione routing
- `src/css/` — Stili globali (SCSS)

## Comandi utili

```bash
bun run dev      # Dev server con hot reload
bun run build    # Build per produzione
bun run lint     # Linting
```
