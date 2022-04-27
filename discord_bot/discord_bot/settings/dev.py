from base import *

DEBUG = True

ALLOWED_HOSTS = ["localhost","0.0.0.0",".ngrok.io"]

BOT_NAME = "Marbotest"

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]