"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2019 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase

from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask


class RunTasksNonEagerlyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="user1")

    @mock.patch('ESSArch_Core.WorkflowEngine.dbtask.DBTask.apply_async')
    def test_run_with_args(self, apply_async):
        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            args=[5, 10],
            eager=False,
        )
        t.run()

        expected_headers = {
            'responsible': None, 'ip': None, 'step': None, 'step_pos': 0, 'hidden': None,
            'allow_failure': False
        }
        apply_async.assert_called_once_with(
            args=[5, 10], kwargs={}, headers={'headers': expected_headers}, link_error=None,
            queue='celery', task_id=str(t.celery_id),
        )

    @mock.patch('ESSArch_Core.WorkflowEngine.dbtask.DBTask.apply_async')
    def test_run_with_params(self, apply_async):
        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            params={'foo': 'bar'},
            eager=False,
        )
        t.run()

        expected_headers = {
            'responsible': None, 'ip': None, 'step': None, 'step_pos': 0, 'hidden': None,
            'allow_failure': False
        }
        apply_async.assert_called_once_with(
            args=[], kwargs={'foo': 'bar'}, headers={'headers': expected_headers},
            link_error=None, queue='celery', task_id=str(t.celery_id),
        )

    @mock.patch('ESSArch_Core.WorkflowEngine.dbtask.DBTask.apply_async')
    def test_run_with_step(self, apply_async):
        step = ProcessStep.objects.create()
        t = ProcessTask.objects.create(
            name="ESSArch_Core.WorkflowEngine.tests.tasks.Add",
            processstep=step,
            processstep_pos=2,
            eager=False,
        )
        t.run()

        expected_headers = {
            'responsible': None, 'ip': None, 'step': str(step.pk), 'step_pos': 2, 'hidden': None,
            'allow_failure': False
        }
        apply_async.assert_called_once_with(
            args=[], kwargs={}, headers={'headers': expected_headers},
            link_error=None, queue='celery', task_id=str(t.celery_id),
        )


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
        self.assertNotEqual(task.traceback, '')
        self.assertEqual(
            task.exception,
            {
                'exc_type': 'ValueError',
                'exc_message': ('An error occurred!',),
                'exc_module': 'builtins'
            }
        )

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
