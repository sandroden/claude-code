---
name: django-startproject
description: Scaffold a new Django backend project 
context: fork
argument-hint: "<folder-name> [django-project-name]"
---

# Django Startproject

Scaffold a Django project with uv, direnv, Docker and GitLab CI pre-configured.

Arguments (from `/django-startproject <folder> [name]`):
- `$ARGUMENTS[0]` — project folder name (required, ask if missing)
- `$ARGUMENTS[1]` — Django project name: `core` or `web` (ask if missing, offer both as choices)

## Default Configuration

| Option | Value |
|--------|-------|
| Package manager | uv |
| Python | System default (uv managed) |
| direnv | `.envrc` with `source .venv/bin/activate` |
| Docker | Dockerfile based on `thuxit/upython:3.13-16-uv-bookworm` |
| CI | `.gitlab-ci.yml` for Docker image build |

## Workflow

1. Determine the **folder name** from `$ARGUMENTS[0]` or ask the user.
2. Determine the **Django project name** from `$ARGUMENTS[1]` or ask the user (offer `core` or `web`).
3. Run the scaffold script:

```bash
bash <skill_path>/scripts/scaffold.sh <folder-name> <django-project-name>
```

The script:
- Creates the project folder
- Runs `uv init --name <name>-project --no-readme` and `uv add django dj_cmd`
- Adds `ipython` as dev dependency
- Runs `uv run django-admin startproject <name> .`
- Converts `settings.py` to a settings folder (base/dev/staging/production)
- Creates `apps/` directory and patches `manage.py` with `sys.path.insert`
- Adds redirect `/` → `/admin` in urls.py
- Creates `.envrc`, `CLAUDE.md`, `Dockerfile`, `.dockerignore`, `.gitlab-ci.yml`
- Creates superuser `admin` if `~/.config/jmb.conf` has `JMB_PASSWORD`

4. Inform the user the project is ready.

## Important Notes

- The Django project name **must be asked** if not provided: offer `core` or `web` as choices.
- Do NOT initialize git automatically — the user prefers mercurial.
- The Dockerfile references `DJANGO_SETTINGS_MODULE=core.settings` by default; the script updates it automatically if a different project name is used.
- The `IMAGE_NAME` path in `.gitlab-ci.yml` may need manual adjustment for the specific project.
