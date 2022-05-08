from .base import *

DEBUG = True

ALLOWED_HOSTS = ["localhost","0.0.0.0",".ngrok.io"]

BOT_NAME = "Marbotest"

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# HTTPS settings
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False