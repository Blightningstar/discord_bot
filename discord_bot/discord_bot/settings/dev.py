from .base import *

test_mode = os.getenv("TEST_MODE")
DEBUG = test_mode if test_mode else False

ALLOWED_HOSTS = ["localhost","0.0.0.0",".ngrok.io"]

BOT_NAME = "Marbotest"

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# HTTPS settings
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False