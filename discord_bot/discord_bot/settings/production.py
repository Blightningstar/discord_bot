from .base import *

test_mode = os.getenv("TEST_MODE")

if test_mode=="True":
    DEBUG = True
    ALLOWED_HOSTS = [".herokuapp.com", "localhost", "0.0.0.0"]
else: 
    DEBUG = False
    ALLOWED_HOSTS = [".herokuapp.com"]

BOT_NAME = "Marbot"