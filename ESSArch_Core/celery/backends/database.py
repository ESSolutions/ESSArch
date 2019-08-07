import sys

import celery.exceptions
from celery.backends.base import BaseDictBackend
from celery.states import EXCEPTION_STATES, READY_STATES, STARTED, SUCCESS
from celery.utils.serialization import create_exception_cls
from django.db.models import F
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

        ProcessTask.objects.filter(celery_id=task_id).update(**updated)
        return result

    def update_state(self, task_id, meta, status, request=None):
        progress = (meta['current'] / meta['total']) * 100

        ProcessTask.objects.filter(celery_id=task_id).update(
            status=status if status is not None else F('status'),
            meta=meta,
            progress=progress,
        )
        return status

    def _get_task_meta_for(self, task_id):
        obj = ProcessTask.objects.get(celery_id=task_id)
        meta = obj.meta or {}
        meta.update({
            'exception': obj.exception,
            'result': obj.result,
            'status': obj.status,
            'traceback': obj.traceback,
        })
        return meta

    @classmethod
    def exception_to_python(cls, exc):
        """Convert serialized exception to Python exception."""
        if exc:
            if not isinstance(exc, BaseException):
                exc_module = exc.get('exc_module')
                if exc_module is None:
                    cls = create_exception_cls(exc['exc_type'], __name__)
                else:
                    exc_module = exc_module
                    exc_type = exc['exc_type']
                    try:
                        cls = getattr(sys.modules[exc_module], exc_type)
                    except KeyError:
                        cls = create_exception_cls(exc_type, celery.exceptions.__name__)
                exc_msg = exc['exc_message']
                exc = cls(*exc_msg if isinstance(exc_msg, tuple) else exc_msg)
        return exc

    def meta_from_decoded(self, meta):
        if meta['status'] in self.EXCEPTION_STATES:
            meta['result'] = self.exception_to_python(meta['exception'])
        return meta
