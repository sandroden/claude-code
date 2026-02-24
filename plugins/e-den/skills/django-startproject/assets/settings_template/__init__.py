import re
import os
import sys

from .base import *  # noqa

ENABLE_DEBUG_TOOLBAR = False

# no longer links in settings.
# we first check ENV, if exists that determines dev/staging/prod
# local.py: retained just for dev and legacy

if 'ENV' in os.environ:
    settings_env_file = os.path.join(SETTINGS_DIR, os.environ['ENV'] + '.py')  # noqa
else:
    settings_env_file = os.path.join(SETTINGS_DIR, 'settings.py')  # noqa
    if not os.path.exists(settings_env_file):
        print(
            "Imposta ENV o crea il link in __PROJECT_NAME__/settings al file di conf: dev/staging o production")
        sys.exit(1)

# Local settings setup, aimed at dev only
local_settings = os.path.join(SETTINGS_DIR, 'local.py')  # noqa
if 'ENV' in os.environ and os.environ['ENV'] == 'dev' and not os.path.exists(local_settings):
    from django.core.management.utils import get_random_secret_key
    with open(local_settings, 'w') as f:
        f.write('SECRET_KEY = "%s"\n' % get_random_secret_key())

# così non è necessario importare dentro local 'from .base *'
# tutto viene già passato nei 'globals()'
if os.path.exists(settings_env_file):
    exec(compile(open(settings_env_file).read(),
                 settings_env_file, 'exec'), globals())

if os.path.exists(local_settings):
    exec(compile(open(local_settings).read(),
                 local_settings, 'exec'), globals())


if globals().get('SENTRY_DSN_KEY'):  # non cambiare
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    sentry_sdk.init(
        dsn=SENTRY_DSN_KEY,  # noqa
        integrations=[DjangoIntegration()],
        send_default_pii=True
    )

if ENABLE_DEBUG_TOOLBAR:
    DEBUG_TOOLBAR_PATCH_SETTINGS = True
    INSTALLED_APPS += [  # noqa
        'debug_toolbar',
    ]

    TEMPLATES[0]['OPTIONS']['context_processors'] += ["django.template.context_processors.debug"]  # noqa
    MIDDLEWARE[0:0] = ['debug_toolbar.middleware.DebugToolbarMiddleware']  # noqa

for key in os.environ:
    if key.startswith("DJANGO_"):
        var_name = re.sub('DJANGO_', '', key)
        globals()[var_name] = os.environ[key]
