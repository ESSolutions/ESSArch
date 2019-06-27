from celery.backends.base import BaseDictBackend
from celery.states import EXCEPTION_STATES, READY_STATES, STARTED, SUCCESS
from django.utils import timezone

from ESSArch_Core.WorkflowEngine.models import ProcessTask


class DatabaseBackend(BaseDictBackend):
    subpolling_interval = 0.5

    def _store_result(self, task_id, result, status,
                      traceback=None, request=None, using=None):

        """Store return value and status of an executed task."""

        if traceback is None:
            traceback = ''

        updated = {
            'status': status,
            'traceback': traceback,
        }

        if status == STARTED:
            updated['time_started'] = timezone.now()

        if status in READY_STATES:
            updated['time_done'] = timezone.now()

        if status == SUCCESS:
            updated['result'] = result
            updated['progress'] = 100

        if status in EXCEPTION_STATES:
            updated['exception'] = result

        ProcessTask.objects.filter(pk=task_id).update(**updated)
        return result

    def update_state(self, task_id, meta, status, request=None):
        progress = (meta['current'] / meta['total']) * 100

        ProcessTask.objects.filter(pk=task_id).update(
            status=status,
            meta=meta,
            progress=progress,
        )
        return status

    def _get_task_meta_for(self, task_id):
        obj = ProcessTask.objects.get(pk=task_id)
        meta = obj.meta or {}
        meta.update({
            'exception': obj.exception,
            'result': obj.result,
            'status': obj.status,
            'traceback': obj.traceback,
        })
        return meta

    def meta_from_decoded(self, meta):
        if meta['status'] in self.EXCEPTION_STATES:
            meta['result'] = self.exception_to_python(meta['exception'])
        return meta
