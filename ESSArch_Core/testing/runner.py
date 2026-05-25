import logging
from contextlib import contextmanager

from celery import current_app
from django.conf import settings
from django.db import connection
from django.test.runner import DiscoverRunner


class ESSArchTestRunner(DiscoverRunner):
    def run_tests(self, *args, **kwargs):
        # Do not show log messages while testing
        logging.disable(logging.CRITICAL)

        return super().run_tests(*args, **kwargs)

    def setup_databases(self, **kwargs):
        dbs = super().setup_databases(**kwargs)
        if connection.vendor == 'microsoft':
            self._handle_mssql_migrations()
            db_name = connection.settings_dict['NAME']
            connection.creation.install_regex_clr(db_name)
        return dbs

    def _handle_mssql_migrations(self):
        """
        Automatically fix known MSSQL migration issues.
        Runs AFTER DB creation but BEFORE tests execute fully.
        """
        from django.core.management import call_command

        # 1. Ensure token_blacklist is at safe migration state
        # (0008 is the problematic one on MSSQL)
        try:
            call_command(
                "migrate",
                "token_blacklist",
                "0007",
                fake=True,
                verbosity=0,
            )
        except Exception:
            # If already applied or partially applied, ignore
            pass

        # 2. Continue normal migration process
        call_command("migrate", verbosity=0)


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
