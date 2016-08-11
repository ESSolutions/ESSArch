from __future__ import absolute_import, division

import json
import uuid

from celery import states as celery_states, Task

from django.db import models


class StepManager(models.Manager):
    def create_step(self, name, tasks=[], steps=[], waitForParams=False):
        """
        Creates a process step with the given name, tasks and steps

        Args:
            tasks: A dict of tasks containing the name and params of the task
        """

        from preingest.models import ProcessStep, ProcessTask

        step = self.create(
            name=name,
            task_set=[d['name'] for d in tasks],
            waitForParams=waitForParams
        )

        for s in steps:
            s = ProcessStep.objects.create_step(s)
            s.save()
            step.child_steps.add(s)

        attempt = uuid.uuid4()

        for pos, t in enumerate(tasks):
            task = ProcessTask(
                processstep=step,
                processstep_pos=pos,
                name=t["name"],
                params=t["params"],
                attempt=attempt,
                status="PREPARED"
            )

            step.tasks.add(task, bulk=False)

        return step

    def create_step_from_file(self, name):
        newname = name.replace(".", "/").replace("/json", ".json")

        with open(newname) as f:
            data = json.loads(f.read())
            tasks = data.get("tasks", [])
            steps = data.get("steps", [])
            waitForParams = data.get("waitForParams", False)

        return self.create_step(name, tasks=tasks, steps=steps, waitForParams=waitForParams)


class TaskManager(models.Manager):
    pass
