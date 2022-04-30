from base import *

DEBUG = False

ALLOWED_HOSTS = [".herokuapp.com"]

BOT_NAME = "Marbot"

# HTTPS settings
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True