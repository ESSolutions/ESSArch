import logging
import os
import random
import string

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT_SHORTNAME = 'EC'
PROJECT_NAME = 'ESSArch Core'

DEBUG = True
SECRET_KEY = ''.join([random.choice(string.ascii_letters) for x in range(40)])

SITE_ID = 1
ROOT_URLCONF = 'ESSArch_Core.testapp.urls'

INSTALLED_APPS = [
    'allauth',
    'allauth.account',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.sites',
    'django_filters',
    'groups_manager',
    'nested_inline',
    'rest_auth',
    'rest_auth.registration',
    'rest_framework',
    'rest_framework.authtoken',
    'mptt',
    'ESSArch_Core.admin',
    'ESSArch_Core.auth',
    'ESSArch_Core.config',
    'ESSArch_Core.configuration',
    'ESSArch_Core.docs',
    'ESSArch_Core.frontend',
    'ESSArch_Core.ip',
    'ESSArch_Core.maintenance',
    'ESSArch_Core.profiles',
    'ESSArch_Core.essxml.Generator',
    'ESSArch_Core.essxml.ProfileMaker',
    'ESSArch_Core.fixity',
    'ESSArch_Core.storage',
    'ESSArch_Core.tags',
    'ESSArch_Core.WorkflowEngine',
    'guardian',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'ESSArch_Core.auth.backends.GroupRoleBackend',
    'guardian.backends.ObjectPermissionBackend',
]

GROUPS_MANAGER = {
    'AUTH_MODELS_SYNC': True,
    'PERMISSIONS': {
        'owner': [],
        'group': [],
        'groups_upstream': [],
        'groups_downstream': [],
        'groups_siblings': [],
    },
    'GROUP_NAME_PREFIX': '',
    'GROUP_NAME_SUFFIX': '',
    'USER_USERNAME_PREFIX': '',
    'USER_USERNAME_SUFFIX': '',
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite',
    }
}

CACHES = {
    'default': {
        'TIMEOUT': None,
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

REST_FRAMEWORK = {
    'DEFAULT_METADATA_CLASS': 'ESSArch_Core.metadata.CustomMetadata',
    'DEFAULT_PAGINATION_CLASS': 'proxy_pagination.ProxyPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'ESSArch_Core.auth.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}

REST_AUTH_SERIALIZERS = {
    'USER_DETAILS_SERIALIZER': 'ESSArch_Core.auth.serializers.UserLoggedInSerializer'
}

PROXY_PAGINATION_PARAM = 'pager'
PROXY_PAGINATION_DEFAULT = 'ESSArch_Core.pagination.LinkHeaderPagination'
PROXY_PAGINATION_MAPPING = {'none': 'ESSArch_Core.pagination.NoPagination'}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/Stockholm'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Disable logging
logging.disable(logging.CRITICAL)
