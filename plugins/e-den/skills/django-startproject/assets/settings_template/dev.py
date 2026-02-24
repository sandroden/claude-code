# Development settings
# Usato quando ENV=dev

DEBUG = True

ALLOWED_HOSTS = ['*']

# CORS / CSRF per development (Quasar dev server sulla porta 9000)
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:9000',
]

# Per development, usiamo sqlite
# In local.py puoi sovrascrivere con PostgreSQL se preferisci
