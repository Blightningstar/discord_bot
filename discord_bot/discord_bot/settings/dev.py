from .base import *

DEBUG = True

ALLOWED_HOSTS = ["localhost","0.0.0.0",".ngrok.io"]

BOT_NAME = "Marbotest"
MUSIC_CHANNEL = 894034318089920542

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "discordBot",
        "USER": "postgres",
        "PASSWORD": "postgrespw",
        "HOST": "localhost",
        "PORT": "49155",
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