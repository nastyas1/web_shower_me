import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "auth-service-dev-secret")
DEBUG = os.environ.get("DEBUG", "0") == "1"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS_AUTH", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "app",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
    ]},
}]

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.environ.get("DB_NAME_AUTH", "auth_db"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST_AUTH", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

LANGUAGE_CODE = "ru"
TIME_ZONE = "Europe/Moscow"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "/auth/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# JWT
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-me-jwt-secret")
JWT_ACCESS_TTL_HOURS = int(os.environ.get("JWT_EXPIRATION_HOURS", "24"))
JWT_REFRESH_TTL_DAYS = 7

# CORS
CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")

# Inter-service communication
AUTH_SERVICE_URL = os.environ.get("AUTH_SERVICE_URL", "http://auth-service:8000")
FEEDBACK_SERVICE_URL = os.environ.get("FEEDBACK_SERVICE_URL", "http://feedback-service:8000")
BOOKING_SERVICE_URL = os.environ.get("BOOKING_SERVICE_URL", "http://booking-service:8000")
COMMENTS_SERVICE_URL = os.environ.get("COMMENTS_SERVICE_URL", "http://comments-service:8000")
