from .base import *

DEBUG = True

ALLOWED_HOSTS = ["localhost","0.0.0.0",".ngrok.io"]

BOT_NAME = "Marbotest"

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