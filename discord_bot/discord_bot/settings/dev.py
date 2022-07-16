from .base import *

DEBUG = True

ALLOWED_HOSTS = ["localhost","0.0.0.0",".ngrok.io"]

BOT_NAME = "Marbotest"
MUSIC_CHANNEL = 894034318089920542

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

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}