import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def cargar_env(ruta):
    if not os.path.exists(ruta):
        return
    with open(ruta, encoding='utf-8') as archivo:
        for linea in archivo:
            linea = linea.strip()
            if not linea or linea.startswith('#') or '=' not in linea:
                continue
            clave, valor = linea.split('=', 1)
            os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def elegir_backend_correo(entorno):
    if entorno.get('EMAIL_BACKEND'):
        return entorno['EMAIL_BACKEND']
    if entorno.get('EMAIL_CLAVE'):
        return 'django.core.mail.backends.smtp.EmailBackend'
    return 'cuentas.correo.ConsolaLegibleBackend'


def elegir_remitente(entorno):
    if entorno.get('EMAIL_REMITENTE'):
        return entorno['EMAIL_REMITENTE']
    if entorno.get('EMAIL_USUARIO'):
        return f"Aventuras del Sur <{entorno['EMAIL_USUARIO']}>"
    return 'Aventuras del Sur <no-responder@aventuradelsur.cl>'


CLAVE_SECRETA_DE_DESARROLLO = 'django-insecure-x7q2m9b4k1w8z5r3t6y0u2i4o6p8a1s3d5f7g9h1j3k5l7'


def elegir_debug(entorno):
    return entorno.get('DJANGO_DEBUG', '1').strip().lower() in ('1', 'true', 'si', 'yes')


def elegir_hosts(entorno):
    valor = entorno.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
    return [host.strip() for host in valor.split(',') if host.strip()]


def elegir_clave_secreta(entorno, debug):
    clave = entorno.get('DJANGO_SECRET_KEY', '').strip() or CLAVE_SECRETA_DE_DESARROLLO
    if not debug and clave == CLAVE_SECRETA_DE_DESARROLLO:
        raise ImproperlyConfigured(
            'Con DJANGO_DEBUG=0 es obligatorio definir DJANGO_SECRET_KEY con una clave propia.'
        )
    return clave


cargar_env(BASE_DIR / '.env')

DEBUG = elegir_debug(os.environ)

SECRET_KEY = elegir_clave_secreta(os.environ, DEBUG)

ALLOWED_HOSTS = elegir_hosts(os.environ)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'cuentas',
    'experiencias',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'inventarioAventura.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'inventarioAventura.wsgi.application'

if os.environ.get('USAR_SQLITE') == '1':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    try:
        import pymysql
        pymysql.version_info = (2, 2, 1, 'final', 0)
        pymysql.install_as_MySQLdb()
    except ImportError:
        pass

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NOMBRE', 'inventarioaventura'),
            'USER': os.environ.get('DB_USUARIO', 'aventura'),
            'PASSWORD': os.environ.get('DB_CLAVE', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PUERTO', '3306'),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-cl'

TIME_ZONE = 'America/Santiago'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'cuentas.Usuario'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'panel'
LOGOUT_REDIRECT_URL = 'inicio'

SESSION_COOKIE_AGE = 1800
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

EMAIL_BACKEND = elegir_backend_correo(os.environ)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_USUARIO', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_CLAVE', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', '1') == '1'
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = elegir_remitente(os.environ)

PASSWORD_RESET_TIMEOUT = 3600
