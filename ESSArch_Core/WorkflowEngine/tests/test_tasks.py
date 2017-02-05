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

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from ESSArch_Core.ip.models import (
    InformationPackage,
)

from ESSArch_Core.WorkflowEngine.models import (
    ProcessTask,
)


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

    def test_run_with_wrong_params(self):
        """
        Runs a task with nonexistent parameters.
        """

        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

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

        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

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

        with self.assertNumQueries(4):
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
            task = ProcessTask.objects.create(
                name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
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


class test_undoing_tasks(TestCase):
    def setUp(self):
        settings.CELERY_ALWAYS_EAGER = True
        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

    def test_undo_successful_task(self):
        x = 2
        y = 1

        task = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            params={'x': x, 'y': y}
        )

        task.run()
        self.assertEqual(task.status, celery_states.SUCCESS)

        res = task.undo()
        self.assertEqual(res.get(), x-y)
        self.assertTrue(task.undone)
        self.assertFalse(task.undo_type)
        self.assertFalse(task.retried)

        self.assertEqual(task.status, celery_states.SUCCESS)

        undo_task = ProcessTask.objects.get(name="ESSArch_Core.WorkflowEngine.tests.tasks.Add", undo_type=True)
        self.assertIsNotNone(undo_task)
        self.assertTrue(undo_task.undo_type)

    def test_undo_failed_task(self):
        task = ProcessTask.objects.create(name="ESSArch_Core.WorkflowEngine.tests.tasks.Fail")

        with self.assertRaises(Exception):
            task.run()

        self.assertEqual(task.status, celery_states.FAILURE)

        task.undo()
        self.assertTrue(task.undone)
        self.assertFalse(task.undo_type)
        self.assertFalse(task.retried)
        self.assertEqual(task.status, celery_states.FAILURE)

        undo_task = ProcessTask.objects.get(name="ESSArch_Core.WorkflowEngine.tests.tasks.Fail", undo_type=True)
        self.assertIsNotNone(undo_task)
        self.assertTrue(undo_task.undo_type)


class test_retrying_tasks(TestCase):

    @classmethod
    def setUpClass(cls):
        settings.CELERY_ALWAYS_EAGER = True
        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

        cls.root = os.path.dirname(os.path.realpath(__file__))
        cls.datadir = os.path.join(cls.root, "datadir")

        try:
            os.mkdir(cls.datadir)
        except OSError as e:
            if e.errno == 17:  # file exists
                shutil.rmtree(cls.datadir)
                os.mkdir(cls.datadir)
            else:
                raise

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.datadir)

    def test_retry_successful_task(self):
        x = 2
        y = 1

        task = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            params={'x': x, 'y': y}
        )

        task.run()
        task.undo()
        task.retry()

        self.assertTrue(task.undone)
        self.assertFalse(task.undo_type)
        self.assertTrue(task.retried)
        self.assertEqual(task.status, celery_states.SUCCESS)

        undo_task = ProcessTask.objects.get(name="ESSArch_Core.WorkflowEngine.tests.tasks.Add", undo_type=True)
        self.assertIsNotNone(undo_task)
        self.assertTrue(undo_task.undo_type)

        retry_task = ProcessTask.objects.get(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            undo_type=False, undone=False
        )
        self.assertIsNotNone(retry_task)
        self.assertFalse(retry_task.undone)
        self.assertFalse(retry_task.undo_type)
        self.assertFalse(retry_task.retried)
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
            undo_type=False, undone=False
        )
        self.assertIsNotNone(retry_task)
        self.assertFalse(retry_task.undone)
        self.assertFalse(retry_task.undo_type)
        self.assertFalse(retry_task.retried)
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

        retry_task = ProcessTask.objects.get(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.FailIfFileNotExists",
            undo_type=False, undone=False
        )
        self.assertIsNotNone(retry_task)
        self.assertFalse(retry_task.undone)
        self.assertFalse(retry_task.undo_type)
        self.assertFalse(retry_task.retried)
        self.assertEqual(retry_task.status, celery_states.SUCCESS)
        self.assertEqual(task.status, celery_states.FAILURE)
