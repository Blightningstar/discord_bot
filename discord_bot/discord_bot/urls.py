"""discord_bot URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

import os

from django.contrib import admin
from django.urls import include, path

from .views import home

if os.getenv("DJANGO_ENV") == "PROD":
    from discord_bot.settings.production import BOT_NAME
elif os.getenv("DJANGO_ENV") == "DEV":
    from discord_bot.settings.dev import BOT_NAME

url_bot_name = str(BOT_NAME).lower()
urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path(f"{url_bot_name}/", include("music_bot.urls")),
]
