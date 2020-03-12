import logging
from contextlib import contextmanager

from celery import current_app
from django.conf import settings
from django.db import connection
from django.db.backends.base.creation import TEST_DATABASE_PREFIX
from django.test.runner import DiscoverRunner


class ESSArchTestRunner(DiscoverRunner):
    def run_tests(self, *args, **kwargs):
        # Do not show log messages while testing
        logging.disable(logging.CRITICAL)

        return super().run_tests(*args, **kwargs)

    def setup_databases(self, **kwargs):
        dbs = super().setup_databases(**kwargs)
        if connection.vendor == 'microsoft':
            db_name = connection.settings_dict['NAME']
            connection.creation.install_regex_clr(db_name)
        return dbs


@contextmanager
def TaskRunner(propagate=True):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    current_app.conf.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = propagate
    current_app.conf.CELERY_TASK_EAGER_PROPAGATES = propagate
    yield
    current_app.conf.CELERY_TASK_ALWAYS_EAGER = False
    settings.CELERY_TASK_ALWAYS_EAGER = False
    settings.CELERY_TASK_EAGER_PROPAGATES = False
    current_app.conf.CELERY_TASK_EAGER_PROPAGATES = False
