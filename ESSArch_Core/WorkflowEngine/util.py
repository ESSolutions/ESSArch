from celery import states as celery_states
from celery.result import AsyncResult

from ESSArch_Core.WorkflowEngine.models import ProcessTask


def get_result(pk, eager=False):
    if not eager and AsyncResult(str(pk)).successful():
        return AsyncResult(str(pk)).result
    else:
        return ProcessTask.objects.values_list('result', flat=True).get(pk=pk, status=celery_states.SUCCESS)
