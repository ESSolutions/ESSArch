from django.conf.urls import include, url

from ESSArch_Core.WorkflowEngine.views import ProcessTaskViewSet, ProcessStepViewSet
from ESSArch_Core.ip.views import InformationPackageViewSet, WorkareaEntryViewSet
from ESSArch_Core.routers import ESSArchRouter

router = ESSArchRouter()
router.register(r'information-packages', InformationPackageViewSet)
router.register(r'steps', ProcessStepViewSet)
router.register(r'tasks', ProcessTaskViewSet)
router.register(r'workarea-entries', WorkareaEntryViewSet, base_name='workarea-entries')

urlpatterns = [
    url(r'^api/', include(router.urls)),
]
