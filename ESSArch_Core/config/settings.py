import os
from datetime import timedelta
from urllib.parse import urlparse

import dj_database_url

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT_SHORTNAME = 'ESSArch'
PROJECT_NAME = 'ESSArch'

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

ESSARCH_TRANSFORMERS = {
    'content': 'fixity.transformation.backends.content.ContentTransformer'
}

ESSARCH_WORKFLOW_POLLERS = {
    'dir': {
        'class': 'workflow.polling.backends.directory.DirectoryWorkflowPoller',
        'path': '/ESSArch/data/eta/reception/eft',
    }
}

try:
    from local_essarch_settings import REDIS_URL
except ImportError:
    REDIS_URL = os.environ.get('REDIS_URL_ESSARCH', 'redis://localhost/1')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'essarch_secret_key'
SESSION_COOKIE_NAME = 'essarch'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# XSD is not listed in any mime types on macOS
if DEBUG:
    import mimetypes
    mimetypes.add_type("application/xml", ".xsd", True)

# Set test runner
TEST_RUNNER = "ESSArch_Core.testing.runner.QuietTestRunner"

ALLOWED_HOSTS = ['*']

REST_FRAMEWORK = {
    'DEFAULT_METADATA_CLASS': 'ESSArch_Core.api.metadata.CustomMetadata',
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

PROXY_PAGINATION_PARAM = 'pager'
PROXY_PAGINATION_DEFAULT = 'ESSArch_Core.api.pagination.LinkHeaderPagination'
PROXY_PAGINATION_MAPPING = {'none': 'ESSArch_Core.api.pagination.NoPagination'}


# Application definition

INSTALLED_APPS = [
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'channels',
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django_filters',
    'groups_manager',
    'guardian',
    'mptt',
    'nested_inline',
    'rest_auth',
    'rest_auth.registration',
    'rest_framework',
    'rest_framework.authtoken',
    'ESSArch_Core.admin',
    'ESSArch_Core.api',
    'ESSArch_Core.auth',
    'ESSArch_Core.config',
    'ESSArch_Core.configuration',
    'ESSArch_Core.docs',
    'ESSArch_Core.frontend',
    'ESSArch_Core.ip',
    'ESSArch_Core.profiles',
    'ESSArch_Core.essxml.Generator',
    'ESSArch_Core.essxml.ProfileMaker',
    'ESSArch_Core.fixity',
    'ESSArch_Core.maintenance',
    'ESSArch_Core.search',
    'ESSArch_Core.stats',
    'ESSArch_Core.storage',
    'ESSArch_Core.tags',
    'ESSArch_Core.WorkflowEngine',
    'ESSArch_Core.workflow',
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

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}
ASGI_APPLICATION = 'ESSArch_Core.routing.application'

SITE_ID = 1

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

CORS_ORIGIN_ALLOW_ALL = True
ROOT_URLCONF = 'ESSArch_Core.config.urls'

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

WSGI_APPLICATION = 'ESSArch_Core.config.wsgi.application'


# Database
try:
    from local_essarch_settings import DATABASE_URL
except ImportError:
    DATABASE_URL = os.environ.get('DATABASE_URL_ESSARCH', 'sqlite:///db.sqlite')
DATABASES = {'default': dj_database_url.parse(url=DATABASE_URL)}

# Cache
REDIS_CLIENT_CLASS = os.environ.get('REDIS_CLIENT_CLASS', 'redis.client.StrictRedis')
DJANGO_REDIS_CONNECTION_FACTORY = os.environ.get('DJANGO_REDIS_CONNECTION_FACTORY',
                                                 'django_redis.pool.ConnectionFactory')

CACHES = {
    'default': {
        'TIMEOUT': None,
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'REDIS_CLIENT_CLASS': REDIS_CLIENT_CLASS,
        }
    }
}

try:
    from local_essarch_settings import ELASTICSEARCH_URL
except ImportError:
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL', 'http://localhost:9200')
elasticsearch_url = urlparse(ELASTICSEARCH_URL)
ELASTICSEARCH_CONNECTIONS = {
    'default': {
        'hosts': [{
            'host': elasticsearch_url.hostname,
            'port': elasticsearch_url.port,
            'timeout': 60,
        }],
    }
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(message)s'
        },
    },
    'handlers': {
        'core': {
            'level': 'DEBUG',
            'class': 'ESSArch_Core.log.dbhandler.DBHandler',
            'application': 'ESSArch',
            'agent_role': 'Producer',
        },
        'file_essarch': {
            'level': 'DEBUG',
            'formatter': 'verbose',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/ESSArch/log/essarch.log',
            'maxBytes': 1024 * 1024 * 100,  # 100MB
            'backupCount': 5,
        },
        'log_file_auth': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'filename': '/ESSArch/log/auth.log',
            'maxBytes': 1024 * 1024 * 100,  # 100MB
            'backupCount': 5,
        },
    },
    'loggers': {
        'essarch': {
            'handlers': ['core', 'file_essarch'],
            'level': 'DEBUG',
        },
        'essarch.auth': {
            'level': 'DEBUG',
            'handlers': ['log_file_auth'],
            'propagate': False,
        },
    },
}

# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Django Rest Auth serializers
# http://django-rest-auth.readthedocs.io/en/latest/configuration.html

REST_AUTH_SERIALIZERS = {
    'USER_DETAILS_SERIALIZER': 'ESSArch_Core.auth.serializers.UserLoggedInSerializer'
}

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/?ref=logout'

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_COOKIE_NAME = 'essarch_language'
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Stockholm'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Media files
MEDIA_URL = 'api/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.environ.get('STATIC_ROOT_ESSARCH', os.path.join(BASE_DIR, 'static_root'))
STATICFILES_DIRS = (os.path.join('static'),)

DJANGO_REV_MANIFEST_PATH = os.path.join(BASE_DIR, 'frontend/static/frontend/build/rev-manifest.json')

# Documentation
DOCS_ROOT = os.path.join(BASE_DIR, 'docs/_build/{lang}/html')

# Celery settings
try:
    from local_essarch_settings import RABBITMQ_URL
except ImportError:
    RABBITMQ_URL = os.environ.get('RABBITMQ_URL_ESSARCH', 'amqp://guest:guest@localhost:5672')
CELERY_BROKER_URL = RABBITMQ_URL
CELERY_IMPORTS = (
    "ESSArch_Core.ip.tasks",
    "ESSArch_Core.tasks",
    "ESSArch_Core.WorkflowEngine.tests.tasks",
    "preingest.tasks",
    "workflow.tasks",
)
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_BROKER_HEARTBEAT = 0
CELERY_BROKER_TRANSPORT_OPTIONS = {'confirm_publish': True}

CELERY_BEAT_SCHEDULE = {
    'RunWorkflowProfiles-every-10-seconds': {
        'task': 'ESSArch_Core.tasks.RunWorkflowProfiles',
        'schedule': timedelta(seconds=10),
    },
    'PollAccessQueue-every-10-seconds': {
        'task': 'workflow.tasks.PollAccessQueue',
        'schedule': timedelta(seconds=10),
    },
    'PollIOQueue-every-10-seconds': {
        'task': 'workflow.tasks.PollIOQueue',
        'schedule': timedelta(seconds=10),
    },
    'PollRobotQueue-queue-every-10-seconds': {
        'task': 'workflow.tasks.PollRobotQueue',
        'schedule': timedelta(seconds=10),
    },
    'UnmountIdleDrives-queue-every-10-seconds': {
        'task': 'workflow.tasks.UnmountIdleDrives',
        'schedule': timedelta(seconds=10),
    },
    'PollAppraisalJobs-every-10-seconds': {
        'task': 'workflow.tasks.PollAppraisalJobs',
        'schedule': timedelta(seconds=10),
    },
    'ScheduleAppraisalJobs-every-10-seconds': {
        'task': 'workflow.tasks.ScheduleAppraisalJobs',
        'schedule': timedelta(seconds=10),
    },
    'PollConversionJobs-every-10-seconds': {
        'task': 'workflow.tasks.PollConversionJobs',
        'schedule': timedelta(seconds=10),
    },
    'ScheduleConversionJobs-every-10-seconds': {
        'task': 'workflow.tasks.ScheduleConversionJobs',
        'schedule': timedelta(seconds=10),
    },
    'IndexTags': {
        'task': 'ESSArch_Core.tasks.IndexTags',
        'schedule': timedelta(seconds=10),
    },
    'UpdateTags': {
        'task': 'ESSArch_Core.tasks.UpdateTags',
        'schedule': timedelta(seconds=10),
    },
    'DeleteTags': {
        'task': 'ESSArch_Core.tasks.DeleteTags',
        'schedule': timedelta(seconds=10),
    },
    'ClearTagProcessQueue': {
        'task': 'ESSArch_Core.tasks.ClearTagProcessQueue',
        'schedule': timedelta(seconds=10),
    },
}

# Rest auth settings
OLD_PASSWORD_FIELD_ENABLED = True

try:
    from local_essarch_settings import *  # noqa isort:skip
except ImportError:
    pass
