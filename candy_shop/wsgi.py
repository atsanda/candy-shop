"""
WSGI config for candy_shop project.
It exposes the WSGI callable as a module-level variable named ``application``.
For more information on this file, see
https://docs.djangoproject.com/en/2.0/howto/deployment/wsgi/gunicorn/
"""
import os
from dotenv import load_dotenv

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "candy_shop.config")
os.environ.setdefault("DJANGO_CONFIGURATION", "Production")

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

from configurations.wsgi import get_wsgi_application
application = get_wsgi_application()
