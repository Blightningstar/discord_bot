from .base import *

DEBUG = False

ALLOWED_HOSTS = [".herokuapp.com"]

BOT_NAME = "Marbot"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "dnqo7edhna8sk",
        "USER": "jpfwcyherkxjak",
        "PASSWORD": "7357b601741e4e797d5d27e97c793ecf89ce1b324da00735f26e1200613f1bf4",
        "HOST": "ec2-44-205-41-76.compute-1.amazonaws.com",
        "PORT": "5432",
    }
}

# HTTPS settings
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}