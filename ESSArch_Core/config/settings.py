import os
import tarfile
from datetime import timedelta
from urllib.parse import quote_plus as urlquote, urlparse

import environ

from ESSArch_Core import BASE_DIR

env = environ.Env()
ESSARCH_DIR = env.str('ESSARCH_DIR', '/ESSArch')
env.read_env(os.path.join(ESSARCH_DIR, 'config', 'essarch_env'))
CONFIG_DIR = env.str('ESSARCH_CONFIG_DIR', os.path.join(ESSARCH_DIR, 'config'))

PROJECT_SHORTNAME = 'ESSArch'
PROJECT_NAME = 'ESSArch'
SESSION_COOKIE_NAME = env.str('ESSARCH_SESSION_COOKIE_NAME', 'essarch')
SESSION_COOKIE_SECURE = env.bool('ESSARCH_SESSION_COOKIE_SECURE', default=True)
CSRF_COOKIE_SECURE = env.bool('ESSARCH_CSRF_COOKIE_SECURE', default=True)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('ESSARCH_DEBUG', default=True)

# XSD is not listed in any mime types on macOS
if DEBUG:
    import mimetypes
    mimetypes.add_type("application/xml", ".xsd", True)

try:
    from local_essarch_settings import REDIS_URL
except ImportError:
    REDIS_URL = env.str('ESSARCH_REDIS_URL', env.str('REDIS_URL_ESSARCH', env.str('REDIS_URL', 'redis://localhost/1')))

# Workflow Pollers
ESSARCH_WORKFLOW_POLLERS = {}

# Set test runner
TEST_RUNNER = "ESSArch_Core.testing.runner.ESSArchTestRunner"

ALLOWED_HOSTS = env.list('ESSARCH_ALLOWED_HOSTS', default=['*'])

# Exclude file formats keys from content indexing. Example: ['fmt/569',]
EXCLUDE_FILE_FORMAT_FROM_INDEXING_CONTENT = env.list('ESSARCH_EXCLUDE_FILE_FORMAT_FROM_INDEXING_CONTENT', default=[])

# Verify TLS certificate on remote servers
#
# From requests docs:
# Either a boolean, in which case it controls whether we verify
# the server’s TLS certificate, or a string, in which case it
# must be a path to a CA bundle to use.
REQUESTS_VERIFY = env.bool('ESSARCH_REQUESTS_VERIFY', default=True)

REST_FRAMEWORK = {
    'DEFAULT_METADATA_CLASS': 'ESSArch_Core.api.metadata.CustomMetadata',
    'DEFAULT_PAGINATION_CLASS': 'proxy_pagination.ProxyPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'ESSArch_Core.auth.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'knox.auth.TokenAuthentication',
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

# Add support to extract zipfiles with "\" as separator in pathname components
OS_PATH_ALTSEP = env.str('ESSARCH_OS_PATH_ALTSEP', "\\")

# Application definition

INSTALLED_APPS = env.list('ESSARCH_INSTALLED_APPS', default=[
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'channels',
    'corsheaders',
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django_filters',
    'django_json_widget',
    'countries_plus',
    'languages_plus',
    'groups_manager',
    'guardian',
    'mptt',
    'nested_inline',
    'dj_rest_auth',
    'dj_rest_auth.registration',
    'rest_framework',
    'knox',
    'ESSArch_Core.admin',
    'ESSArch_Core.access',
    'ESSArch_Core.agents',
    'ESSArch_Core.api',
    'ESSArch_Core.auth',
    'ESSArch_Core.config',
    'ESSArch_Core.configuration',
    'ESSArch_Core.docs',
    'ESSArch_Core.essarch',
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
])
INSTALLED_APPS.extend(env.list('ESSARCH_INSTALLED_APPS_EXTRA', default=[]))

try:
    import test_without_migrations  # noqa
except ImportError:
    pass
else:
    INSTALLED_APPS.append('test_without_migrations')

AUTHENTICATION_BACKENDS = env.list('ESSARCH_AUTHENTICATION_BACKENDS', default=[
    'django.contrib.auth.backends.ModelBackend',
    'ESSArch_Core.auth.backends.GroupRoleBackend',
    'guardian.backends.ObjectPermissionBackend',
])
AUTHENTICATION_BACKENDS.extend(env.list('ESSARCH_AUTHENTICATION_BACKENDS_EXTRA', default=[]))

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

MIDDLEWARE = env.list('ESSARCH_MIDDLEWARE', default=[
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
])
MIDDLEWARE.extend(env.list('ESSARCH_MIDDLEWARE_EXTRA', default=[]))

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
env.DB_SCHEMES['mssql'] = 'mssql'
try:
    from local_essarch_settings import DATABASE_URL
    DATABASES = {'default': env.db_url_config(DATABASE_URL)}
except ImportError:
    DATABASES = {'default': env.db_url('ESSARCH_DATABASE_URL', default=env.str(
        'DATABASE_URL_ESSARCH', default='sqlite:///db.sqlite'))}
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Cache
REDIS_CLIENT_CLASS = env.str('ESSARCH_REDIS_CLIENT_CLASS', 'redis.client.StrictRedis')
DJANGO_REDIS_CONNECTION_FACTORY = env.str('ESSARCH_DJANGO_REDIS_CONNECTION_FACTORY',
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
    ELASTICSEARCH_URL = env.str('ESSARCH_ELASTICSEARCH_URL', env.str('ELASTICSEARCH_URL', 'http://localhost:9200'))
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
if elasticsearch_url.username is not None and elasticsearch_url.password is not None:
    ELASTICSEARCH_CONNECTIONS['default']['http_auth'] = (
        elasticsearch_url.username + ':' + urlquote(elasticsearch_url.password))
if elasticsearch_url.scheme == 'https':
    ELASTICSEARCH_CONNECTIONS['default']['hosts'][0]['use_ssl'] = True

try:
    from local_essarch_settings import ELASTICSEARCH_TEST_URL
except ImportError:
    ELASTICSEARCH_TEST_URL = env.str('ESSARCH_ELASTICSEARCH_TEST_URL', env.str(
        'ELASTICSEARCH_TEST_URL', 'http://localhost:19200'))
elasticsearch_test_url = urlparse(ELASTICSEARCH_TEST_URL)
ELASTICSEARCH_TEST_CONNECTIONS = {
    'default': {
        'hosts': [
            {
                'host': elasticsearch_test_url.hostname,
                'port': elasticsearch_test_url.port,
            },
        ],
        'timeout': 10,
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
TARFILE_FORMAT = tarfile.GNU_FORMAT

# Logging
LOGGING_DIR = os.path.join(ESSARCH_DIR, 'log')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(message)s'
        },
        'verbose_process': {
            'format': '%(asctime)s %(levelname)s %(module)s %(process)d %(thread)d %(message)s'
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
            'filename': os.path.join(LOGGING_DIR, 'essarch.log'),
            'maxBytes': 1024 * 1024 * 100,  # 100MB
            'backupCount': 5,
        },
        # 'file_essarch_db': {
        #     'level': 'DEBUG',
        #     'formatter': 'verbose',
        #     'class': 'logging.handlers.RotatingFileHandler',
        #     'filename': os.path.join(LOGGING_DIR, 'essarch_db.log'),
        #     'maxBytes': 1024 * 1024 * 100,  # 100MB
        #     'backupCount': 5,
        # },
        'log_file_auth': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'filename': os.path.join(LOGGING_DIR, 'auth.log'),
            'maxBytes': 1024 * 1024 * 100,  # 100MB
            'backupCount': 5,
        },
        # 'log_file_ldap': {
        #    'level': 'DEBUG',
        #    'class' : 'logging.handlers.RotatingFileHandler',
        #    'formatter': 'verbose',
        #    'filename': os.path.join(LOGGING_DIR, 'ldap.log'),
        #    'maxBytes': 1024*1024*100, # 100MB
        #    'backupCount': 5,
        # },
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
        # 'django.db.backends': {
        #     'handlers': ['file_essarch_db'],
        #     'level': 'DEBUG',
        # },
        'essarch': {
            'handlers': ['core', 'file_essarch'],
            'level': 'DEBUG',
        },
        'essarch.auth': {
            'level': 'DEBUG',
            'handlers': ['log_file_auth'],
            'propagate': False,
        },
        # 'djangosaml2': {
        #    'level': 'DEBUG',
        #    'handlers': ['log_file_auth'],
        #    'propagate': True,
        # },
        # 'saml2': {
        #    'level': 'DEBUG',
        #    'handlers': ['log_file_auth'],
        #    'propagate': True,
        # },
        # 'django_auth_ldap': {
        #    'level': 'DEBUG',
        #    'handlers': ['log_file_ldap'],
        #    'propagate': False,
        # },
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
# https://dj-rest-auth.readthedocs.io/en/latest/configuration.html

REST_AUTH = {
    'USER_DETAILS_SERIALIZER': 'ESSArch_Core.auth.serializers.UserLoggedInSerializer',
    'TOKEN_MODEL': None,
}

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/?ref=logout'

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_COOKIE_NAME = 'essarch_language'
LANGUAGE_CODE = 'en-us'

LOCALE_PATHS = [os.path.join(BASE_DIR, 'locale')]

TIME_ZONE = 'Europe/Stockholm'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = os.path.join(ESSARCH_DIR, 'config/essarch/media')

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = env.str('ESSARCH_STATIC_ROOT', os.path.join(ESSARCH_DIR, 'config/essarch/static_root'))
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
    RABBITMQ_URL = env.str('ESSARCH_RABBITMQ_URL', env.str(
        'RABBITMQ_URL_ESSARCH', 'amqp://guest:guest@localhost:5672'))
CELERY_BROKER_URL = RABBITMQ_URL
CELERY_IMPORTS = (
    "ESSArch_Core.fixity.action.tasks",
    "ESSArch_Core.ip.tasks",
    "ESSArch_Core.maintenance.tasks",
    "ESSArch_Core.preingest.tasks",
    "ESSArch_Core.storage.tasks",
    "ESSArch_Core.tags.tasks",
    "ESSArch_Core.tasks",
    "ESSArch_Core.workflow.tasks",
    "ESSArch_Core.WorkflowEngine.tests.tasks",
)
CELERY_RESULT_BACKEND = 'processtask'
CELERY_BROKER_HEARTBEAT = 0
CELERY_BROKER_TRANSPORT_OPTIONS = {'confirm_publish': True}
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = False
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
    'PollAppraisalJobs-every-10-minutes': {
        'task': 'ESSArch_Core.maintenance.tasks.PollAppraisalJobs',
        'schedule': timedelta(minutes=10),
    },
    'PollConversionJobs-every-10-minutes': {
        'task': 'ESSArch_Core.maintenance.tasks.PollConversionJobs',
        'schedule': timedelta(minutes=10),
    },
    # 'PollRobotQueue-every-10-seconds': {
    #     'task': 'ESSArch_Core.workflow.tasks.PollRobotQueue',
    #     'schedule': timedelta(seconds=10),
    # },
    # 'UnmountIdleDrives-every-20-seconds': {
    #     'task': 'ESSArch_Core.workflow.tasks.UnmountIdleDrives',
    #     'schedule': timedelta(seconds=20),
    # },
}

CELERY_BEAT_SCHEDULE_FILENAME = os.path.join(ESSARCH_DIR, 'config/essarch/celerybeat-schedule')

# Rest auth settings
OLD_PASSWORD_FIELD_ENABLED = True

try:
    from local_essarch_settings import *  # noqa isort:skip
except ImportError as e:
    if e.name == 'local_essarch_settings':
        raise ImportError('No settings file found, create one by running `essarch settings generate`')
    raise
