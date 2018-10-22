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

import mock
from celery import states as celery_states
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask
from ESSArch_Core.ip.models import InformationPackage


class RunTasksNonEagerlyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="user1")

    @mock.patch('ESSArch_Core.tasks.DBTask.apply_async')
    def test_run_with_args(self, apply_async):
        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            args=[5, 10],
            eager=False,
        )
        t.run()

        expected_options = {'responsible': None, 'ip': None, 'step': None, 'step_pos': 0, 'hidden': False}
        apply_async.assert_called_once_with(args=[5, 10], kwargs={'_options': expected_options}, link_error=None,
                                            queue='celery', task_id=str(t.pk))

    @mock.patch('ESSArch_Core.tasks.DBTask.apply_async')
    def test_run_with_params(self, apply_async):
        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            params={'foo': 'bar'},
            eager=False,
        )
        t.run()

        expected_options = {'responsible': None, 'ip': None, 'step': None, 'step_pos': 0, 'hidden': False}
        apply_async.assert_called_once_with(args=[], kwargs={'foo': 'bar', '_options': expected_options},
                                            link_error=None, queue='celery', task_id=str(t.pk))

    @mock.patch('ESSArch_Core.tasks.DBTask.apply_async')
    def test_run_with_step(self, apply_async):
        step = ProcessStep.objects.create()
        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            processstep=step,
            processstep_pos=2,
            eager=False,
        )
        t.run()

        expected_options = {'responsible': None, 'ip': None, 'step': step.pk, 'step_pos': 2, 'hidden': False}
        apply_async.assert_called_once_with(args=[], kwargs={'_options': expected_options},
                                            link_error=None, queue='celery', task_id=str(t.pk))


class OnSuccessTests(TestCase):
    def test_on_success(self):
        """
        Runs a correct task and checks if the result is saved and that the
        traceback is empty.
        """

        foo = 123

        task = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.First",
            params={"foo": foo},
            eager=True,
        )

        task.run()

        task.refresh_from_db()
        self.assertFalse(task.traceback)
        self.assertEqual(foo, task.result)


class OnFailureTests(TestCase):
    def test_on_failure(self):
        """
        Runs a failing task and checks if the result is empty and that the
        traceback is nonempty.
        """

        task = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Fail",
            eager=True,
        )

        with self.assertRaises(Exception):
            task.run().get()

        task.refresh_from_db()
        self.assertIsNone(task.result)
        self.assertIsNotNone(task.traceback)
        self.assertEqual(u"Exception: An error occurred!", task.exception)

    def test_on_failure_does_not_exist(self):
        """
        Runs a task that fails because an object does not exist
        """

        task = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.FailDoesNotExist",
            eager=True,
        )

        with self.assertRaises(InformationPackage.DoesNotExist):
            task.run().get()

        task.refresh_from_db()
        self.assertIsNone(task.result)
        self.assertIsNotNone(task.traceback)


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
            task.run().get()

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
