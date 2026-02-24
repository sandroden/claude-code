#!/bin/bash
set -e

PROJECT_NAME="${1:?Usage: scaffold.sh <project-name> [description] [mode]}"
DESCRIPTION="${2:-A Quasar Project}"
MODE="${3:-spa}"
ORIG_DIR="$(pwd)"
TARGET_DIR="${ORIG_DIR}/$PROJECT_NAME"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Validate mode
case "$MODE" in
  spa|ssr|pwa) ;;
  *) echo "ERROR: Invalid mode '$MODE'. Valid: spa, ssr, pwa"; exit 1 ;;
esac

if [ -d "$TARGET_DIR" ]; then
  echo "ERROR: Directory '$TARGET_DIR' already exists."
  exit 1
fi

echo "==> Creating Quasar project: $PROJECT_NAME"
echo "    Mode: $MODE"
echo "    Target: $TARGET_DIR"
echo ""

# Create a temporary runner directory for installing create-quasar
RUNNER_DIR=$(mktemp -d)
trap 'rm -rf "$RUNNER_DIR"' EXIT

# Install create-quasar and prompts in the same node_modules
# (so they share the same prompts instance for override to work)
cat > "$RUNNER_DIR/package.json" << 'PKGJSON'
{"name":"cq-runner","private":true,"type":"module"}
PKGJSON

echo "==> Installing create-quasar..."
cd "$RUNNER_DIR" && bun add create-quasar prompts 2>/dev/null

# Write the automation script that overrides all interactive prompts
# projectFolder is just the name — create-quasar resolves it relative to CWD
cat > "$RUNNER_DIR/run.mjs" << ENDSCRIPT
import prompts from 'prompts';

prompts.override({
  projectType: 'app',
  projectFolder: '${PROJECT_NAME}',
  scriptType: 'ts',
  engine: 'vite-2',
  name: '${PROJECT_NAME}',
  productName: '${PROJECT_NAME}',
  description: '${DESCRIPTION}',
  sfcStyle: 'composition-setup',
  css: 'scss',
  preset: ['eslint', 'pinia'],
  prettier: true,
  packageManager: false
});

// Prevent create-quasar from resetting our overrides
prompts.override = () => {};

await import('create-quasar');
ENDSCRIPT

# Run from the ORIGINAL directory so the project is created there
echo "==> Scaffolding project (non-interactive)..."
cd "$ORIG_DIR"
node "$RUNNER_DIR/run.mjs"

echo ""
echo "==> Installing dependencies with bun..."
cd "${TARGET_DIR}"
bun install

# Add mode if not SPA (SPA is the default, no extra setup needed)
if [ "$MODE" != "spa" ]; then
  echo "==> Adding Quasar $MODE mode..."
  bunx quasar mode add "$MODE"
fi

# Copy Dockerfile and related files based on mode
echo "==> Copying Dockerfile, .gitlab-ci.yml, CLAUDE.md..."
if [ "$MODE" = "ssr" ]; then
  cp "$SKILL_DIR/assets/Dockerfile.ssr" ./Dockerfile
else
  cp "$SKILL_DIR/assets/Dockerfile" .
  cp "$SKILL_DIR/assets/nginx.conf" .
fi
cp "$SKILL_DIR/assets/gitlab-ci.yml" .gitlab-ci.yml
cp "$SKILL_DIR/assets/CLAUDE.md" .
# Update CLAUDE.md with actual mode
sed -i "s|__MODE__|${MODE}|g" ./CLAUDE.md

# Add devServer proxy to quasar.config.ts for /api, /admin, /static, /media
echo "==> Adding proxy configuration to quasar.config.ts..."
QCONF="${TARGET_DIR}/quasar.config.ts"
# Add comma after "open: true" and insert proxy block
sed -i 's|open: true // opens browser window automatically|open: true, // opens browser window automatically|' "$QCONF"
sed -i '/open: true,/a\
      proxy: {\
        '"'"'/api'"'"': {\
          target: '"'"'http://localhost:8000'"'"',\
          changeOrigin: true\
        },\
        '"'"'/admin'"'"': {\
          target: '"'"'http://localhost:8000'"'"',\
          changeOrigin: true\
        },\
        '"'"'/static'"'"': {\
          target: '"'"'http://localhost:8000'"'"',\
          changeOrigin: true\
        },\
        '"'"'/media'"'"': {\
          target: '"'"'http://localhost:8000'"'"',\
          changeOrigin: true\
        }\
      }' "$QCONF"

echo ""
echo "============================================"
echo "  Project created: ${PROJECT_NAME}"
echo "  Mode: ${MODE}"
echo "  Path: ${TARGET_DIR}"
echo ""
echo "  cd ${PROJECT_NAME} && bun run dev"
echo "============================================"
