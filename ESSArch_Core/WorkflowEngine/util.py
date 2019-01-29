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
def _create_step(parent_step, flow, ip, responsible, context=None):
    if context is None:
        context = {}
    for e_idx, flow_entry in enumerate(flow):
        if not flow_entry.get('if', True):
            continue

        if flow_entry.get('step', False):
            if len(flow_entry.get('children', [])) == 0:
                # no child steps or tasks in step, no need to create step
                continue

            child_s = ProcessStep.objects.create(
                name=flow_entry['name'],
                parent_step=parent_step,
                parent_step_pos=e_idx,
                information_package=ip,
                context=context,
            )

            on_error_tasks = _create_on_error_tasks(flow_entry.get('on_error', []), ip=ip, responsible=responsible)
            for on_error_task in on_error_tasks:
                child_s.on_error.add(on_error_task)

            _create_step(child_s, flow_entry['children'], ip, responsible, context=context)
        else:
            args = flow_entry.get('args', [])
            params = flow_entry.get('params', {})
            task = ProcessTask.objects.create(
                name=flow_entry['name'],
                label=flow_entry.get('label'),
                args=args,
                params=params,
                eager=False,
                information_package=ip,
                responsible=responsible,
                processstep=parent_step,
                processstep_pos=e_idx,
            )

            on_error_tasks = _create_on_error_tasks(flow_entry.get('on_error', []), ip=ip, responsible=responsible)
            for on_error_task in on_error_tasks:
                task.on_error.add(on_error_task)


@transaction.atomic
def create_workflow(workflow_spec, ip=None, name='', on_error=None, eager=False, context=None):
    if on_error is None:
        on_error = []
    if context is None:
        context = {}
    root_step = ProcessStep.objects.create(name=name, eager=eager, context=context)
    responsible = getattr(ip, 'responsible', None)

    for on_error_task in _create_on_error_tasks(on_error, ip=ip, responsible=responsible):
        root_step.on_error.add(on_error_task)

    _create_step(root_step, workflow_spec, ip, responsible)
    return root_step
