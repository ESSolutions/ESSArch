import logging
import sys

import celery.exceptions
from celery.backends.base import BaseDictBackend
from celery.states import (
    EXCEPTION_STATES,
    FAILURE,
    READY_STATES,
    STARTED,
    SUCCESS,
)
from celery.utils.serialization import create_exception_cls
from django.db.models import F
from django.utils import timezone
from django.utils.translation import ugettext as _
from kombu.utils.encoding import from_utf8

from ESSArch_Core.auth.models import Notification
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

        if not ProcessTask.objects.filter(celery_id=task_id, status=FAILURE, allow_failure=True).exists():
            if status == SUCCESS:
                updated['result'] = result
                updated['progress'] = 100

            if status in EXCEPTION_STATES:
                updated['exception'] = result
        else:
            updated.pop('traceback')
            updated.pop('status')

        ProcessTask.objects.filter(celery_id=task_id).update(**updated)

        if status in EXCEPTION_STATES:
            t = ProcessTask.objects.get(celery_id=task_id)
            if t.responsible is not None:
                t_name = t.label or t.name
                Notification.objects.create(
                    message=_('"%(task)s" failed' % {'task': t_name}),
                    level=logging.ERROR,
                    user=t.responsible,
                    refresh=True,
                )
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
                    cls = create_exception_cls(
                        from_utf8(exc['exc_type']), __name__)
                else:
                    exc_module = from_utf8(exc_module)
                    exc_type = from_utf8(exc['exc_type'])
                    try:
                        # Load module and find exception class in that
                        cls = sys.modules[exc_module]
                        # The type can contain qualified name with parent classes
                        for name in exc_type.split('.'):
                            cls = getattr(cls, name)
                    except (KeyError, AttributeError):
                        cls = create_exception_cls(exc_type,
                                                   celery.exceptions.__name__)
                exc_msg = exc['exc_message']
                try:
                    if isinstance(exc_msg, (tuple, list)):
                        exc = cls(*exc_msg)
                    else:
                        exc = cls(exc_msg)
                except Exception as err:  # noqa
                    exc = Exception('{}({})'.format(cls, exc_msg))
        return exc

    def meta_from_decoded(self, meta):
        if meta['status'] in self.EXCEPTION_STATES:
            meta['result'] = self.exception_to_python(meta['exception'])
        return meta
