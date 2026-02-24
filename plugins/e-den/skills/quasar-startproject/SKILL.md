---
name: quasar-startproject
description: Scaffold a new Quasar (Vue.js) frontend project with TypeScript, Pinia, Vue Router, ESLint, Prettier, Vite, and SCSS pre-configured. Supports SPA (default), SSR, and PWA modes. Includes Dockerfile, GitLab CI, proxy to Django backend, and CLAUDE.md. Use when the user asks to create a frontend project, scaffold a Quasar app, start a new Quasar project, or says things like "voglio il frontend", "crea il frontend", "crea un progetto Quasar", "nuovo progetto Quasar", "scaffold Quasar". Automates the interactive `create-quasar` CLI so no manual input is needed.
argument-hint: "<folder-name> [description] [spa|ssr|pwa]"
---

# Quasar Startproject

Scaffold a Quasar v2 frontend project fully automated, without interactive prompts.

Arguments (from `/quasar-startproject <folder> [description] [mode]`):
- `$ARGUMENTS[0]` — project folder name (required, ask if missing)
- `$ARGUMENTS[1]` — description (optional, default: `"A Quasar Project"`)
- `$ARGUMENTS[2]` — mode: `spa` (default), `ssr`, or `pwa` (ask only if user mentions SSR/PWA)

## Default Configuration

| Option | Value |
|--------|-------|
| Framework | Quasar v2 + Vue 3 |
| Language | TypeScript |
| Build tool | Vite |
| Component style | Composition API (`<script setup>`) |
| CSS preprocessor | SCSS |
| State management | Pinia |
| Linting | ESLint + Prettier |
| Package manager | bun |
| Mode | `spa` (default), `ssr`, or `pwa` |
| Docker | bun build + nginx (SPA/PWA) or bun build + node (SSR) |
| CI | `.gitlab-ci.yml` for Docker image build |
| Proxy | `/api`, `/admin`, `/static`, `/media` → `localhost:8000` |

## Workflow

1. Determine the **folder name** from `$ARGUMENTS[0]` or ask the user.
2. Determine the **description** from `$ARGUMENTS[1]` or use default.
3. Determine the **mode** from `$ARGUMENTS[2]` or from context. Default is `spa`.
4. Run the scaffold script:

```bash
bash <skill_path>/scripts/scaffold.sh <folder-name> [description] [mode]
```

The script:
- Scaffolds a base Quasar project (non-interactive via `prompts.override()`)
- Runs `bun install`
- If mode is `ssr` or `pwa`, runs `bunx quasar mode add <mode>`
- Copies the appropriate Dockerfile: nginx-based (SPA/PWA) or node-based (SSR)
- Copies `.gitlab-ci.yml` and `CLAUDE.md`
- Patches `quasar.config.ts` with devServer proxy

5. Inform the user the project is ready.

## Modes

| Mode | Dockerfile | Production server | Extra files |
|------|-----------|-------------------|-------------|
| `spa` | bun build → nginx:80 | nginx (static) | `nginx.conf` |
| `pwa` | bun build → nginx:80 | nginx (static) | `nginx.conf`, `src-pwa/` |
| `ssr` | bun build → node:3000 | bun (Node.js) | `src-ssr/` |

## Important Notes

- The script creates the project in the **current working directory**.
- If the target folder already exists, the script exits with an error.
- Do NOT initialize git automatically — the user prefers mercurial.
- The proxy assumes Django backend runs on port 8000.
- The `IMAGE_NAME` path in `.gitlab-ci.yml` may need manual adjustment.

## Customization

Valid `prompts.override()` options (modify script if needed):

- `scriptType`: `'ts'` or `'js'`
- `engine`: `'vite-2'` or `'webpack-4'`
- `sfcStyle`: `'composition-setup'`, `'composition'`, or `'options'`
- `css`: `'scss'`, `'sass'`, or `'css'`
- `preset`: any combination of `['eslint', 'pinia', 'axios', 'i18n']`
- `prettier`: `true` or `false`
