from celery import states as celery_states
from celery.result import AsyncResult

from django.db import transaction

from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask


def get_result(pk, eager=False):
    if not eager and AsyncResult(str(pk)).successful():
        return AsyncResult(str(pk)).result
    else:
        return ProcessTask.objects.values_list('result', flat=True).get(pk=pk, status=celery_states.SUCCESS)


def _create_on_error_tasks(l, ip=None, responsible=None):
    for on_error_idx, on_error in enumerate(l):
        args = on_error.get('args', [])
        params = on_error.get('params', {})
        yield ProcessTask.objects.create(
            name=on_error['name'],
            label=on_error.get('label'),
            hidden=on_error.get('hidden', False),
            args=args,
            params=params,
            eager=False,
            information_package=ip,
            responsible=responsible,
            processstep_pos=on_error_idx,
        )


@transaction.atomic
def _create_step(parent_step, flow, ip, responsible):
    for t_idx, task in enumerate(flow):
        if not task.get('if', True):
            continue

        if task.get('step', False):
            child_s = ProcessStep.objects.create(
                name=task['name'],
                parent_step=parent_step,
                parent_step_pos=t_idx,
                information_package=ip,
            )

            for on_error_task in _create_on_error_tasks(task.get('on_error', []), ip=ip, responsible=responsible):
                child_s.on_error.add(on_error_task)

            _create_step(child_s, task['children'], ip, responsible)
        else:
            args = task.get('args', [])
            params = task.get('params', {})
            ProcessTask.objects.create(
                name=task['name'],
                label=task.get('label'),
                args=args,
                params=params,
                eager=False,
                information_package=ip,
                responsible=responsible,
                processstep=parent_step,
                processstep_pos=t_idx,
            )


@transaction.atomic
def create_workflow(workflow_spec, ip=None, name='', on_error=None, eager=False):
    root_step = ProcessStep.objects.create(name=name, eager=eager)
    if on_error is None:
        on_error = []
    responsible = getattr(ip, 'responsible', None)

    for on_error_task in _create_on_error_tasks(on_error, ip=ip, responsible=responsible):
        root_step.on_error.add(on_error_task)

    _create_step(root_step, workflow_spec, ip, responsible)
    return root_step
