"""
WSGI config for discord_bot project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

if os.getenv("DJANGO_ENV") == "PROD":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "discord_bot.settings.production")
else:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "discord_bot.settings.dev")

application = get_wsgi_application()
