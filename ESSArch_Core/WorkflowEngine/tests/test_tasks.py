"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Core
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

import os
import shutil
import traceback

from celery import states as celery_states

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from ESSArch_Core.configuration.models import (
    EventType
)

from ESSArch_Core.ip.models import (
    EventIP,
    InformationPackage,
)

from ESSArch_Core.WorkflowEngine.models import (
    ProcessTask,
)


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
class test_running_tasks(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="user1")

    def test_create_nonexistent_task(self):
        """
        Creates a task with a name that doesn't exist.
        """

        with self.assertRaises(ValidationError):
            task = ProcessTask.objects.create(
                name="nonexistent task",
                responsible=self.user
            )

            task.full_clean()

    def test_create_existing_task(self):
        """
        Creates a task with a name that does exist.
        """

        task = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            responsible=self.user
        )

        task.full_clean()

    def test_run_with_args(self):
        x = 5
        y = 10

        res = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            args=[x, y],
            information_package=InformationPackage.objects.create()
        ).run().get()

        self.assertEqual(res, x+y)

    def test_run_with_too_many_args(self):
        x = 5
        y = 10

        with self.assertRaisesRegexp(TypeError, 'takes exactly 3 arguments'):
            ProcessTask.objects.create(
                name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
                args=[x, y, 15],
                information_package=InformationPackage.objects.create()
            ).run()

    def test_run_with_wrong_params(self):
        """
        Runs a task with nonexistent parameters.
        """

        with self.assertRaises(TypeError):
            task = ProcessTask.objects.create(
                name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
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

        with self.assertRaises(TypeError):
            task = ProcessTask.objects.create(
                name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
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
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={
                "foo": foo
            },
            information_package=InformationPackage.objects.create()
        )

        with self.assertNumQueries(3):
            task.run()

        task.refresh_from_db()
        self.assertFalse(task.traceback)
        self.assertEqual(foo, task.result)

    def test_on_success_with_event(self):
        EventType.objects.create(eventType=1)

        foo = 123

        task = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.WithEvent",
            params={
                "foo": foo
            },
            information_package=InformationPackage.objects.create()
        )

        with self.assertNumQueries(6):
            task.run()

        task.refresh_from_db()
        self.assertFalse(task.traceback)
        self.assertEqual(foo, task.result)

        e = EventIP.objects.get(eventApplication=task.pk)
        self.assertEqual(e.eventOutcome, 0)
        self.assertEqual(e.eventOutcomeDetailNote, "Task completed successfully with foo=%s" % foo)
        self.assertEqual(e.eventApplication, task)

    def test_on_failure(self):
        """
        Runs an incorrect task and checks if the result is empty and that the
        traceback is nonempty.
        """

        foo = 123
        task = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={
                "bar": foo
            },
            information_package=InformationPackage.objects.create()
        )

        with self.assertNumQueries(3):
            with self.assertRaises(TypeError):
                task.run()

        task.refresh_from_db()

        self.assertIsNone(task.result)
        self.assertIsNotNone(task.traceback)
        self.assertEqual(u"TypeError: run() got an unexpected keyword argument 'bar'", task.exception)

    def test_on_failure_does_not_exist(self):
        """
        Runs a task that fails becuase an object does not exist
        """

        task = ProcessTask.objects.create(name="ESSArch_Core.WorkflowEngine.tests.tasks.FailDoesNotExist")

        with self.assertRaises(InformationPackage.DoesNotExist):
            task.run()

    def test_on_failure_with_event(self):
        EventType.objects.create(eventType=1)

        foo = 123
        task = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.WithEvent",
            params={
                "bar": foo
            },
            information_package=InformationPackage.objects.create()
        )

        with self.assertNumQueries(6):
            with self.assertRaises(TypeError):
                task.run()

        task.refresh_from_db()

        self.assertIsNone(task.result)
        self.assertIsNotNone(task.traceback)
        self.assertEqual(u"TypeError: run() got an unexpected keyword argument 'bar'", task.exception)

        e = EventIP.objects.get(eventApplication=task.pk)
        self.assertEqual(e.eventOutcome, 1)
        self.assertEqual(e.eventOutcomeDetailNote, task.traceback)
        self.assertEqual(e.eventApplication, task)


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
class test_undoing_tasks(TestCase):
    def test_undo_successful_task(self):
        x = 2
        y = 1

        task = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            params={'x': x, 'y': y}
        )

        task.run()
        task.refresh_from_db()
        self.assertEqual(task.status, celery_states.SUCCESS)

        with self.assertNumQueries(5):
            res = task.undo()
        task.refresh_from_db()
        self.assertEqual(res.get(), x-y)

        undo_task = ProcessTask.objects.get(name="ESSArch_Core.WorkflowEngine.tests.tasks.Add", undo_type=True)

        self.assertEqual(task.undone, undo_task)
        self.assertFalse(task.undo_type)
        self.assertIsNone(task.retried)
        self.assertEqual(task.status, celery_states.SUCCESS)
        self.assertTrue(undo_task.undo_type)

    def test_undo_failed_task(self):
        task = ProcessTask.objects.create(name="ESSArch_Core.WorkflowEngine.tests.tasks.Fail")

        with self.assertRaises(Exception):
            task.run()

        task.refresh_from_db()
        self.assertEqual(task.status, celery_states.FAILURE)

        task.undo()
        task.refresh_from_db()

        undo_task = ProcessTask.objects.get(name="ESSArch_Core.WorkflowEngine.tests.tasks.Fail", undo_type=True)
        self.assertEqual(task.undone, undo_task)

        self.assertFalse(task.undo_type)
        self.assertIsNone(task.retried)
        self.assertEqual(task.status, celery_states.FAILURE)
        self.assertTrue(undo_task.undo_type)

    def test_undo_with_args(self):
        x = 2
        y = 1

        task = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            args=[x, y],
        )

        task.run()
        res = task.undo()
        task.refresh_from_db()

        self.assertEqual(res.get(), x-y)


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
class test_retrying_tasks(TestCase):

    def setUp(self):
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno == 17:  # file exists
                shutil.rmtree(self.datadir)
                os.mkdir(self.datadir)
            else:
                raise

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_retry_successful_task(self):
        x = 2
        y = 1

        task = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            params={'x': x, 'y': y}
        )

        task.run()
        task.undo()

        with self.assertNumQueries(5):
            task.retry()

        task.refresh_from_db()

        self.assertFalse(task.undo_type)
        self.assertEqual(task.status, celery_states.SUCCESS)

        undo_task = ProcessTask.objects.get(name="ESSArch_Core.WorkflowEngine.tests.tasks.Add", undo_type=True)
        self.assertEqual(task.undone, undo_task)
        self.assertTrue(undo_task.undo_type)

        retry_task = ProcessTask.objects.get(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            undo_type=False, undone__isnull=True
        )
        self.assertIsNotNone(retry_task)
        self.assertEqual(task.retried, retry_task)
        self.assertIsNone(retry_task.undone)
        self.assertFalse(retry_task.undo_type)
        self.assertIsNone(retry_task.retried)
        self.assertEqual(retry_task.status, celery_states.SUCCESS)

    def test_retry_failed_task(self):
        task = ProcessTask.objects.create(name="ESSArch_Core.WorkflowEngine.tests.tasks.Fail")

        with self.assertRaises(Exception):
            task.run()

        task.undo()

        with self.assertRaises(Exception):
            task.retry()

        retry_task = ProcessTask.objects.get(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Fail",
            undo_type=False, undone__isnull=True
        )
        self.assertIsNotNone(retry_task)
        self.assertEqual(task.retried, retry_task)
        self.assertIsNone(retry_task.undone)
        self.assertFalse(retry_task.undo_type)
        self.assertIsNone(retry_task.retried)
        self.assertEqual(retry_task.status, celery_states.FAILURE)

    def test_retry_failed_fixed_task(self):
        fname = os.path.join(self.datadir, 'foo.txt')

        task = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.FailIfFileNotExists",
            params={"filename": fname}
        )

        with self.assertRaises(AssertionError):
            task.run().get()

        task.undo()

        open(fname, 'a').close()

        task.retry()
        task.refresh_from_db()

        retry_task = ProcessTask.objects.get(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.FailIfFileNotExists",
            undo_type=False, undone__isnull=True
        )
        self.assertIsNotNone(retry_task)
        self.assertEqual(task.retried, retry_task)
        self.assertIsNone(retry_task.undone)
        self.assertFalse(retry_task.undo_type)
        self.assertIsNone(retry_task.retried)
        self.assertEqual(retry_task.status, celery_states.SUCCESS)
        self.assertEqual(task.status, celery_states.FAILURE)

    def test_retry_with_args(self):
        x = 2
        y = 1

        task = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            args=[x, y]
        )

        task.run()
        task.undo()
        res = task.retry().get()

        self.assertEqual(res, x+y)
