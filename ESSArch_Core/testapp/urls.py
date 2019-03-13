from django.conf.urls import include, url

from ESSArch_Core.WorkflowEngine.views import ProcessTaskViewSet, ProcessStepViewSet
from ESSArch_Core.agents.views import AgentViewSet
from ESSArch_Core.ip.views import InformationPackageViewSet, WorkareaEntryViewSet
from ESSArch_Core.maintenance.views import AppraisalRuleViewSet, AppraisalJobViewSet, ConversionJobViewSet
from ESSArch_Core.profiles.views import ProfileViewSet, SubmissionAgreementViewSet
from ESSArch_Core.routers import ESSArchRouter

router = ESSArchRouter()
router.register(r'agents', AgentViewSet)
router.register(r'appraisal-rules', AppraisalRuleViewSet)
router.register(r'appraisal-jobs', AppraisalJobViewSet)
router.register(r'conversion-jobs', ConversionJobViewSet)
router.register(r'information-packages', InformationPackageViewSet)
router.register(r'profiles', ProfileViewSet)
router.register(r'steps', ProcessStepViewSet)
router.register(r'submission-agreements', SubmissionAgreementViewSet)
router.register(r'tasks', ProcessTaskViewSet)
router.register(r'workarea-entries', WorkareaEntryViewSet, base_name='workarea-entries')

urlpatterns = [
    url(r'^api/', include(router.urls)),
]
