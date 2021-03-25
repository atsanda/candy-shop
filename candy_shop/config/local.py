import os
from .common import Common
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Local(Common):
    DEBUG = True

    SECRET_KEY = 'q65e6)4@%ah=n-#(6^0g=p-a+3ffs#28s=l4nda-dufv=)x^95'

    # Testing
    INSTALLED_APPS = Common.INSTALLED_APPS

    # Mail
    EMAIL_HOST = 'localhost'
    EMAIL_PORT = 1025
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

