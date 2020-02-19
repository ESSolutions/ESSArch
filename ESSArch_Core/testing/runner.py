import logging
from contextlib import contextmanager

from celery import current_app
from django.conf import settings
from django.test.runner import DiscoverRunner


class QuietTestRunner(DiscoverRunner):
    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        # Do not show log messages while testing
        logging.disable(logging.CRITICAL)

        return super().run_tests(test_labels, extra_tests, **kwargs)


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
