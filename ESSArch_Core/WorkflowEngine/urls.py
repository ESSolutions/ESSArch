from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^run_step/(?P<name>[a-zA-Z._]+)/$', views.run_step, name='run_step'),
    url(r'^continue_step/(?P<step_id>[-\w]+)/$', views.continue_step, name='continue_step'),
    url(r'^run_task/(?P<name>[a-zA-Z.]+)/$', views.run_task, name='run_task'),
    url(r'^steps/$', views.steps, name='steps'),
    url(r'^tasks/$', views.tasks, name='tasks'),
    url(r'^history/$', views.history, name='history'),
    url(r'^history/(?P<step_id>[-\w]+)/$', views.history_detail, name='history_detail'),
    url(r'^undo_failed/(?P<processstep_id>[-\w]+)/$', views.undo_failed, name='undo_failed'),
    url(r'^undo_step/(?P<processstep_id>[-\w]+)/$', views.undo_step, name='undo_step'),
    url(r'^retry_step/(?P<processstep_id>[-\w]+)/$', views.retry_step, name='retry_step'),
]
