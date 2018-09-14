from django.test import TestCase

from ESSArch_Core.WorkflowEngine.models import ProcessTask, ProcessStep
from ESSArch_Core.WorkflowEngine.util import create_workflow


class CreateWorkflowTestCase(TestCase):
    def test_tasks(self):
        spec = [
            {
                "name": "foo.bar.task",
                "label": "Foo Bar Task",
                "args": [1,2,3],
                "params": {'a': 'b'}
            },
            {
                "name": "foo.bar.task2",
                "label": "Foo Bar Task2",
                "args": [3,2,1],
                "params": {'b': 'a'}
            }
        ]

        create_workflow(spec)

        self.assertEqual(ProcessStep.objects.count(), 1)
        self.assertEqual(ProcessTask.objects.count(), 2)

        step = ProcessStep.objects.get()
        self.assertEqual(step.tasks.count(), 2)
        self.assertEqual(step.tasks.earliest('processstep_pos').name, spec[0]['name'])
        self.assertEqual(step.tasks.latest('processstep_pos').name, spec[1]['name'])
        self.assertEqual(step.on_error.count(), 0)

    def test_steps(self):
        spec = [
            {
                "step": True,
                "name": "My step",
                "children": [
                    {
                        "name": "foo.bar.task",
                        "label": "Foo Bar Task",
                        "args": [1,2,3],
                        "params": {'a': 'b'}
                    },
                    {
                        "name": "foo.bar.task2",
                        "label": "Foo Bar Task2",
                        "args": [3,2,1],
                        "params": {'b': 'a'}
                    }
                ]
            }
        ]

        root_step = create_workflow(spec)

        self.assertEqual(ProcessStep.objects.count(), 2)
        self.assertEqual(ProcessTask.objects.count(), 2)

        self.assertEqual(root_step.tasks.count(), 0)
        self.assertEqual(root_step.child_steps.count(), 1)
        self.assertEqual(root_step.on_error.count(), 0)

        child_step = root_step.child_steps.get()

        self.assertEqual(child_step.tasks.count(), 2)
        self.assertEqual(child_step.child_steps.count(), 0)
        self.assertEqual(child_step.tasks.earliest('processstep_pos').name, spec[0]['children'][0]['name'])
        self.assertEqual(child_step.tasks.latest('processstep_pos').name, spec[0]['children'][1]['name'])
        self.assertEqual(child_step.on_error.count(), 0)

    def test_on_error_task(self):
        spec = [
            {
                "name": "foo.bar.task",
                "label": "Foo Bar Task",
                "args": [1,2,3],
                "params": {'a': 'b'},
                "on_error": [
                    {
                        "name": "foo.bar.task2",
                        "label": "Foo Bar Task2",
                        "args": [3,2,1],
                        "params": {'b': 'a'}
                    }
                ]
            },
        ]

        root_step = create_workflow(spec)

        self.assertEqual(ProcessStep.objects.count(), 1)
        self.assertEqual(ProcessTask.objects.count(), 2)

        self.assertEqual(root_step.tasks.count(), 1)
        self.assertEqual(root_step.child_steps.count(), 0)
        self.assertEqual(root_step.on_error.count(), 0)

        task = root_step.tasks.get()

        self.assertEqual(task.name, spec[0]['name'])
        self.assertEqual(task.on_error.count(), 1)
        self.assertEqual(task.on_error.get().name, spec[0]['on_error'][0]['name'])

    def test_on_error_step(self):
        spec = [
            {
                "step": True,
                "name": "My step",
                "on_error": [
                    {
                        "name": "on_error.task",
                        "label": "On-error Task",
                        "args": [1,2,3],
                        "params": {'a': 'b'},
                    }
                ],
                "children": [
                    {
                        "name": "foo.bar.task",
                        "label": "Foo Bar Task",
                        "args": [1,2,3],
                        "params": {'a': 'b'},
                    }
                ]
            },
        ]

        root_step = create_workflow(spec)

        self.assertEqual(ProcessStep.objects.count(), 2)
        self.assertEqual(ProcessTask.objects.count(), 2)

        self.assertEqual(root_step.tasks.count(), 0)
        self.assertEqual(root_step.child_steps.count(), 1)
        self.assertEqual(root_step.on_error.count(), 0)

        child_step = root_step.child_steps.get()

        self.assertEqual(child_step.name, spec[0]['name'])
        self.assertEqual(child_step.tasks.count(), 1)
        self.assertEqual(child_step.on_error.count(), 1)
        self.assertEqual(child_step.on_error.get().name, spec[0]['on_error'][0]['name'])
