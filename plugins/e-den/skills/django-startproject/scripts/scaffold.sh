#!/bin/bash
set -e

PROJECT_NAME="${1:?Usage: scaffold.sh <project-name> [django-project-name]}"
DJANGO_PROJECT_NAME="${2:-core}"
ORIG_DIR="$(pwd)"
TARGET_DIR="${ORIG_DIR}/$PROJECT_NAME"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ -d "$TARGET_DIR" ]; then
  echo "ERROR: Directory '$TARGET_DIR' already exists."
  exit 1
fi

echo "==> Creating Django project: $PROJECT_NAME"
echo "    Django project name: $DJANGO_PROJECT_NAME"
echo "    Target: $TARGET_DIR"
echo ""

# Create project directory
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

# Initialize uv project (use --name to avoid conflicts, e.g. folder "django" vs package "django")
echo "==> Initializing uv project..."
uv init --name "${DJANGO_PROJECT_NAME}-project" --no-readme

# Clean up uv init artifacts
rm -f main.py
rm -rf .git .gitignore

# Add Django and dj_cmd
echo "==> Adding Django and dj_cmd..."
uv add django dj_cmd

# Add ipython as dev dependency
echo "==> Adding ipython (dev)..."
uv add --dev ipython

# Create Django project
echo "==> Running django-admin startproject $DJANGO_PROJECT_NAME ."
uv run django-admin startproject "$DJANGO_PROJECT_NAME" .

# Convert settings.py to settings/ directory
echo "==> Converting settings to folder structure..."
rm "${TARGET_DIR}/${DJANGO_PROJECT_NAME}/settings.py"
cp -r "$SKILL_DIR/assets/settings_template" "${TARGET_DIR}/${DJANGO_PROJECT_NAME}/settings"
# Replace __PROJECT_NAME__ placeholder with actual django project name
sed -i "s|__PROJECT_NAME__|${DJANGO_PROJECT_NAME}|g" "${TARGET_DIR}/${DJANGO_PROJECT_NAME}/settings/__init__.py"
sed -i "s|__PROJECT_NAME__|${DJANGO_PROJECT_NAME}|g" "${TARGET_DIR}/${DJANGO_PROJECT_NAME}/settings/base.py"
# Create symlink settings.py -> dev.py
cd "${TARGET_DIR}/${DJANGO_PROJECT_NAME}/settings"
ln -s dev.py settings.py
cd "$TARGET_DIR"

# Create apps/ directory
echo "==> Creating apps/ directory..."
mkdir -p "${TARGET_DIR}/apps"
touch "${TARGET_DIR}/apps/.gitkeep"

# Patch manage.py: add sys.path.insert for apps/
echo "==> Patching manage.py (sys.path.insert for apps/)..."
sed -i '/^import sys$/a sys.path.insert(0, "./apps")' "${TARGET_DIR}/manage.py"

# Patch urls.py: add redirect / => /admin
echo "==> Patching urls.py (redirect / => /admin)..."
URLS_FILE="${TARGET_DIR}/${DJANGO_PROJECT_NAME}/urls.py"
sed -i 's|from django.urls import path|from django.urls import path\nfrom django.views.generic import RedirectView|' "$URLS_FILE"
sed -i "s|path('admin/', admin.site.urls),|path('admin/', admin.site.urls),\n    path('', RedirectView.as_view(url='/admin/', permanent=False)),|" "$URLS_FILE"

# Create CLAUDE.md
echo "==> Creating CLAUDE.md..."
cp "$SKILL_DIR/assets/CLAUDE.md" "${TARGET_DIR}/CLAUDE.md"
sed -i "s|__PROJECT_NAME__|${DJANGO_PROJECT_NAME}|g" "${TARGET_DIR}/CLAUDE.md"

# Create .envrc for direnv
echo "==> Setting up direnv (.envrc)..."
echo 'source .venv/bin/activate' > .envrc
direnv allow

# Copy Dockerfile, .dockerignore and .gitlab-ci.yml from skill assets
echo "==> Copying Dockerfile, .dockerignore and .gitlab-ci.yml..."
cp "$SKILL_DIR/assets/Dockerfile" .
cp "$SKILL_DIR/assets/dockerignore" .dockerignore
sed -i "s|__PROJECT_NAME__|${DJANGO_PROJECT_NAME}|g" .dockerignore
cp "$SKILL_DIR/assets/gitlab-ci.yml" .gitlab-ci.yml

# Update DJANGO_SETTINGS_MODULE in Dockerfile if project name is not 'core'
if [ "$DJANGO_PROJECT_NAME" != "core" ]; then
  sed -i "s|DJANGO_SETTINGS_MODULE=core.settings|DJANGO_SETTINGS_MODULE=${DJANGO_PROJECT_NAME}.settings|g" Dockerfile
  sed -i "s|chown -R \${APP_USER} /code/core/settings|chown -R \${APP_USER} /code/${DJANGO_PROJECT_NAME}/settings|g" Dockerfile
fi

# Create superuser if ~/.config/jmb.conf exists and JMB_PASSWORD is defined
JMB_CONF="$HOME/.config/jmb.conf"
if [ -f "$JMB_CONF" ]; then
  JMB_PASSWORD=$(grep -E '^JMB_PASSWORD=' "$JMB_CONF" | cut -d= -f2-)
  if [ -n "$JMB_PASSWORD" ]; then
    echo "==> Creating superuser 'admin'..."
    cd "$TARGET_DIR"
    ENV=dev uv run python manage.py migrate --run-syncdb 2>&1 | tail -1
    ENV=dev DJANGO_SUPERUSER_PASSWORD="$JMB_PASSWORD" uv run python manage.py createsuperuser --noinput --username admin --email admin@localhost
  fi
fi

echo ""
echo "============================================"
echo "  Project created: ${PROJECT_NAME}"
echo "  Django project: ${DJANGO_PROJECT_NAME}"
echo "  Path: ${TARGET_DIR}"
echo ""
echo "  cd ${PROJECT_NAME} && uv run manage.py runserver"
echo "============================================"
