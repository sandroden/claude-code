# Staging settings
# Usato quando ENV=staging

DEBUG = False

ALLOWED_HOSTS = [
    # Aggiungi qui i domini di staging
]

# Database PostgreSQL per staging
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
