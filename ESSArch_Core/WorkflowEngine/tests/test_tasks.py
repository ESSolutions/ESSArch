import traceback

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from install.install_default_config_etp import installDefaultEventTypes

from ESSArch_Core.ip.models import (
    InformationPackage,
)

from ESSArch_Core.WorkflowEngine.models import (
    ProcessTask,
)


def setUpModule():
    installDefaultEventTypes()


class test_running_tasks(TestCase):
    def setUp(self):
        settings.CELERY_ALWAYS_EAGER = True
        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = False

        self.user = User.objects.create(username="user1")

    def test_create_nonexistent_task(self):
        """
        Creates a task with a name that doesn't exist.
        """

        with self.assertRaises(ValidationError):
            task = ProcessTask(
                name="nonexistent task",
                responsible=self.user
            )

            task.full_clean()

    def test_create_existing_task(self):
        """
        Creates a task with a name that does exist.
        """

        task = ProcessTask(
            name="preingest.tests.tasks.First",
            responsible=self.user
        )

        task.full_clean()

    def test_run_with_wrong_params(self):
        """
        Runs a task with nonexistent parameters.
        """

        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

        with self.assertRaises(TypeError):
            task = ProcessTask.objects.create(
                name="preingest.tests.tasks.First",
                params={
                    "bar": 123
                },
                information_package=InformationPackage.objects.create()
            )

            task.run()

    def test_run_with_too_many_params(self):
        """
        Runs a task with too many parameters.
        """

        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

        with self.assertRaises(TypeError):
            task = ProcessTask.objects.create(
                name="preingest.tests.tasks.First",
                params={
                    "foo": 123,
                    "bar": 456
                },
                information_package=InformationPackage.objects.create()
            )

            task.run()

    def test_on_success(self):
        """
        Runs a correct task and checks if the result is saved and that the
        traceback is empty.
        """

        foo = 123

        task = ProcessTask.objects.create(
            name="preingest.tests.tasks.First",
            params={
                "foo": foo
            },
            information_package=InformationPackage.objects.create()
        )

        task.run()
        self.assertIsNone(task.traceback)
        self.assertEqual(foo, task.result)

    def test_on_failure(self):
        """
        Runs an incorrect task and checks if the result is empty and that the
        traceback is nonempty.
        """

        foo = 123
        try:
            task = ProcessTask(
                name="preingest.tests.tasks.First",
                params={
                    "bar": foo
                },
                information_package=InformationPackage.objects.create()
            )
            task.run()
        except TypeError:
            tb = traceback.format_exc()
            self.assertEqual(tb, task.traceback)
            self.assertIsNone(task.result)
            self.assertIsNotNone(task.traceback)
