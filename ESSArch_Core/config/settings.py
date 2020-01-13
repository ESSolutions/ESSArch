import os
from datetime import timedelta
from urllib.parse import urlparse

import dj_database_url

from ESSArch_Core import BASE_DIR

PROJECT_SHORTNAME = 'ESSArch'
PROJECT_NAME = 'ESSArch'

try:
    from local_essarch_settings import REDIS_URL
except ImportError:
    REDIS_URL = os.environ.get('REDIS_URL_ESSARCH', 'redis://localhost/1')

SESSION_COOKIE_NAME = 'essarch'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# XSD is not listed in any mime types on macOS
if DEBUG:
    import mimetypes
    mimetypes.add_type("application/xml", ".xsd", True)


# Workflow Pollers
ESSARCH_WORKFLOW_POLLERS = {
    'dir': {
        'class': 'ESSArch_Core.workflow.polling.backends.directory.DirectoryWorkflowPoller',
        'path': '/ESSArch/data/preingest/reception',
        'sa': 'SA National Archive and Government SE',
    }
}


# Set test runner
TEST_RUNNER = "ESSArch_Core.testing.runner.QuietTestRunner"

ALLOWED_HOSTS = ['*']


# Verify TLS certificate on remote servers
#
# From requests docs:
# Either a boolean, in which case it controls whether we verify
# the server’s TLS certificate, or a string, in which case it
# must be a path to a CA bundle to use.
REQUESTS_VERIFY = True

REST_FRAMEWORK = {
    'DEFAULT_METADATA_CLASS': 'ESSArch_Core.api.metadata.CustomMetadata',
    'DEFAULT_PAGINATION_CLASS': 'proxy_pagination.ProxyPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'ESSArch_Core.auth.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'ESSArch_Core.auth.permissions.ActionPermissions',
    ),
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}

DRF_DYNAMIC_FIELDS = {
    'SUPPRESS_CONTEXT_WARNING': True,
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
    'countries_plus',
    'languages_plus',
    'groups_manager',
    'guardian',
    'mptt',
    'nested_inline',
    'rest_auth',
    'rest_auth.registration',
    'rest_framework',
    'rest_framework.authtoken',
    'ESSArch_Core.admin',
    'ESSArch_Core.agents',
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

try:
    import test_without_migrations  # noqa
except ImportError:
    pass
else:
    INSTALLED_APPS.append('test_without_migrations')

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
            'builtins': ['ESSArch_Core.essxml.templatetags.essxml'],
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
        'hosts': [
            {
                'host': elasticsearch_url.hostname,
                'port': elasticsearch_url.port,
            },
        ],
        'timeout': 60,
        'max_retries': 1,
    }
}

ELASTICSEARCH_INDEXES = {
    'default': {
        'agent': 'ESSArch_Core.agents.documents.AgentDocument',
        'archive': 'ESSArch_Core.tags.documents.Archive',
        'component': 'ESSArch_Core.tags.documents.Component',
        'directory': 'ESSArch_Core.tags.documents.Directory',
        'document': 'ESSArch_Core.tags.documents.File',
        'information_package': 'ESSArch_Core.tags.documents.InformationPackageDocument',
        'structure_unit': 'ESSArch_Core.tags.documents.StructureUnitDocument',
    }
}

ELASTICSEARCH_BATCH_SIZE = 1000

# Storage

ESSARCH_TAPE_IDENTIFICATION_BACKEND = 'base'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(message)s'
        },
        'django.server': {
            '()': 'django.utils.log.ServerFormatter',
            'format': '[{server_time}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
        'django.server': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'django.server',
        },
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
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django.server': {
            'handlers': ['django.server'],
            'level': 'INFO',
            'propagate': True,
        },
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
STATICFILES_DIRS = (os.path.join(BASE_DIR, 'static'),)

DJANGO_REV_MANIFEST_PATH = os.path.join(BASE_DIR, 'frontend/static/frontend/build/rev-manifest.json')

# File upload
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50 MB

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
    "ESSArch_Core.preingest.tasks",
    "ESSArch_Core.storage.tasks",
    "ESSArch_Core.tasks",
    "ESSArch_Core.workflow.tasks",
    "ESSArch_Core.WorkflowEngine.tests.tasks",
)
CELERY_RESULT_BACKEND = 'processtask'
CELERY_BROKER_HEARTBEAT = 0
CELERY_BROKER_TRANSPORT_OPTIONS = {'confirm_publish': True}
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_ACKS_ON_FAILURE_OR_TIMEOUT = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_REMOTE_TRACEBACKS = True
CELERY_TASK_TRACK_STARTED = True

CELERY_BEAT_SCHEDULE = {
    'RunWorkflowPollers-every-60-seconds': {
        'task': 'ESSArch_Core.tasks.RunWorkflowPollers',
        'schedule': timedelta(seconds=60),
    },
    'UnmountIdleDrives-queue-every-10-minutes': {
        'task': 'ESSArch_Core.workflow.tasks.UnmountIdleDrives',
        'schedule': timedelta(minutes=10),
    },
    'PollAppraisalJobs-every-10-minutes': {
        'task': 'ESSArch_Core.workflow.tasks.PollAppraisalJobs',
        'schedule': timedelta(minutes=10),
    },
    'ScheduleAppraisalJobs-every-10-minutes': {
        'task': 'ESSArch_Core.workflow.tasks.ScheduleAppraisalJobs',
        'schedule': timedelta(minutes=10),
    },
    'PollConversionJobs-every-10-minutes': {
        'task': 'ESSArch_Core.workflow.tasks.PollConversionJobs',
        'schedule': timedelta(minutes=10),
    },
    'ScheduleConversionJobs-every-10-minutes': {
        'task': 'ESSArch_Core.workflow.tasks.ScheduleConversionJobs',
        'schedule': timedelta(minutes=10),
    },
}

# Rest auth settings
OLD_PASSWORD_FIELD_ENABLED = True

try:
    from local_essarch_settings import *  # noqa isort:skip
except ImportError as e:
    if e.name == 'local_essarch_settings':
        raise ImportError('No settings file found, create one by running `essarch settings generate`')
    raise
