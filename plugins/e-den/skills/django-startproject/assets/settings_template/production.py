# Production settings
# Usato quando ENV=production

DEBUG = False

ALLOWED_HOSTS = [
    # Aggiungi qui i domini di produzione
]

# Security settings per produzione
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# Database PostgreSQL per produzione
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': '',
#         'USER': '',
#         'PASSWORD': '',  # da local.py o variabile ambiente
#         'HOST': 'localhost',
#         'PORT': '5432',
#     }
# }
