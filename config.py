import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = os.getenv("SECRET_KEY", "WebCar@123")

DEBUG = True

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_NAME = os.getenv("DB_NAME", os.path.join(BASE_DIR, "WEBCAR.FDB"))

DB_USER = os.getenv("DB_USER", "sysdba")
DB_PASSWORD = os.getenv("DB_PASSWORD", "sysdba")