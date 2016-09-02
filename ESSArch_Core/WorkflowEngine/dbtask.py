from __future__ import absolute_import, division

from celery import states as celery_states, Task

from django.utils import timezone

from preingest.models import ProcessTask

class DBTask(Task):
    def __call__(self, *args, **kwargs):
        try:
            self.taskobj = kwargs['taskobj']
        except KeyError:
            print "Task requires taskobj set to a ProcessTask"

        params = self.taskobj.params
        print "init task with name {}, id {}".format(self.name, self.request.id)

        self.taskobj.celery_id = self.request.id
        self.taskobj.status=celery_states.STARTED
        self.taskobj.time_started = timezone.now()
        self.taskobj.save()

        if self.taskobj.undo_type:
            return self.undo(**params)
        else:
            return self.run(**params)

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        print "finalize task with id {}".format(task_id)
        self.taskobj.status = status
        self.taskobj.time_done = timezone.now()
        self.taskobj.save()

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        self.taskobj.traceback = einfo.traceback
        self.taskobj.save()

        ProcessTask.objects.filter(
            attempt=self.taskobj.attempt,
            processstep_pos__gt=self.taskobj.processstep_pos
        ).update(status=celery_states.FAILURE)

    def on_success(self, retval, task_id, args, kwargs):
        self.taskobj.result = retval
        self.taskobj.save()

    def set_progress(self, progress, total=None):
        self.update_state(state=celery_states.PENDING,
                          meta={'current': progress, 'total': total})

        self.taskobj.progress = (progress/total) * 100
        self.taskobj.save()

    def undo(self, *args, **kwargs):
        raise NotImplementedError()
