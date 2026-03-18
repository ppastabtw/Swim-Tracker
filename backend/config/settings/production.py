from .base import *
from decouple import config

DEBUG = False
ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', cast=lambda v: [s.strip() for s in v.split(',')])

CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', cast=lambda v: [s.strip() for s in v.split(',')])
