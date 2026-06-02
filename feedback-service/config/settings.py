import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "feedback-service-dev-secret")
DEBUG = os.environ.get("DEBUG", "0") == "1"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS_FEEDBACK", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "app",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True, "OPTIONS": {}}]

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.environ.get("DB_NAME_FEEDBACK", "feedback_db"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST_FEEDBACK", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

LANGUAGE_CODE = "ru"
TIME_ZONE = "Europe/Moscow"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "/feedback/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# VK API configuration for feedback
VK_GROUP_TOKEN = os.environ.get("VK_GROUP_TOKEN", "")
VK_GROUP_ID = os.environ.get("VK_GROUP_ID", "")
VK_ADMIN_ID = os.environ.get("VK_ADMIN_ID", "")
VK_API_VERSION = "5.131"

# Email configuration
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@shower-booking.com")

# CORS
CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")

# Inter-service communication
AUTH_SERVICE_URL = os.environ.get("AUTH_SERVICE_URL", "http://auth-service:8000")
FEEDBACK_SERVICE_URL = os.environ.get("FEEDBACK_SERVICE_URL", "http://feedback-service:8000")
BOOKING_SERVICE_URL = os.environ.get("BOOKING_SERVICE_URL", "http://booking-service:8000")
COMMENTS_SERVICE_URL = os.environ.get("COMMENTS_SERVICE_URL", "http://comments-service:8000")
