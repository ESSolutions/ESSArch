from celery import states as celery_states
from celery.result import AsyncResult

from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask


def get_result(pk, eager=False):
    if not eager and AsyncResult(str(pk)).successful():
        return AsyncResult(str(pk)).result
    else:
        return ProcessTask.objects.values_list('result', flat=True).get(pk=pk, status=celery_states.SUCCESS)


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


def create_workflow(workflow_spec, ip=None):
    root_step = ProcessStep.objects.create(eager=False)
    responsible = getattr(ip, 'responsible', None)
    _create_step(root_step, workflow_spec, ip, responsible)
    return root_step
