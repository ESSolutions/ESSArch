import traceback

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase

from preingest.models import (
    ProcessTask,
)

class test_running_tasks(TestCase):
    def setUp(self):
        settings.CELERY_ALWAYS_EAGER = True
        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = False

    def test_create_nonexistent_task(self):
        with self.assertRaises(ValidationError):
            task = ProcessTask(
                name="nonexistent task",
            )

            task.full_clean()


    def test_create_existing_task(self):
        task = ProcessTask(
            name="preingest.tasks.First",
        )

        task.full_clean()

    def test_run_with_missing_params(self):
        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

        with self.assertRaises(TypeError):
            task = ProcessTask(
                name="preingest.tasks.First",
            )

            task.run()

    def test_run_with_wrong_params(self):
        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

        with self.assertRaises(TypeError):
            task = ProcessTask(
                name="preingest.tasks.First",
                params={
                    "bar": 123
                }
            )

            task.run()

    def test_run_with_too_many_params(self):
        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

        with self.assertRaises(TypeError):
            task = ProcessTask(
                name="preingest.tasks.First",
                params={
                    "bar": 123
                }
            )

            task.run()

    def test_run_with_correct_params(self):
        foo = 123

        task = ProcessTask(
            name="preingest.tasks.First",
            params={
                "foo": foo
            }
        )

        result = task.run().result

        self.assertIsNone(task.traceback)
        self.assertEqual(foo, result)

    def test_on_success(self):
        foo = 123

        task = ProcessTask(
            name="preingest.tasks.First",
            params={
                "foo": foo
            }
        )

        task.run()

        self.assertIsNone(task.traceback)
        self.assertEqual(foo, task.result)

    def test_on_failure(self):
        foo = 123
        try:
            task = ProcessTask(
                name="preingest.tasks.First",
                params={
                    "bar": foo
                }
            )
            task.run()
        except TypeError:
            tb = traceback.format_exc()
            self.assertEqual(tb, task.traceback)
            self.assertIsNone(task.result)
            self.assertIsNotNone(task.traceback)

