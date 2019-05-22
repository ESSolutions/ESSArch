from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views

from ESSArch_Core.WorkflowEngine.views import ProcessViewSet, ProcessStepViewSet, ProcessTaskViewSet
from ESSArch_Core.auth.views import GroupViewSet, PermissionViewSet, MeView, UserViewSet, NotificationViewSet
from ESSArch_Core.configuration.views import ParameterViewSet, PathViewSet, SiteView, SysInfoView
from ESSArch_Core.fixity.views import ValidationViewSet
from ESSArch_Core.ip.views import AgentViewSet, EventIPViewSet, InformationPackageViewSet, OrderViewSet, \
    WorkareaEntryViewSet, WorkareaViewSet, WorkareaFilesViewSet, InformationPackageReceptionViewSet
from ESSArch_Core.maintenance.views import AppraisalRuleViewSet, AppraisalJobViewSet, ConversionJobViewSet
from ESSArch_Core.profiles.views import ProfileIPViewSet, ProfileIPDataViewSet, ProfileIPDataTemplateViewSet, \
    InformationPackageProfileIPViewSet
from ESSArch_Core.routers import ESSArchRouter
from ESSArch_Core.stats.views import stats, export as export_stats
from ESSArch_Core.configuration.views import EventTypeViewSet
from ESSArch_Core.profiles.views import ProfileViewSet, ProfileSAViewSet, SubmissionAgreementViewSet

admin.site.site_header = 'ESSArch Administration'
admin.site.site_title = 'ESSArch Administration'

router = ESSArchRouter()
router.register(r'users', UserViewSet)
router.register(r'groups', GroupViewSet)
router.register(r'agents', AgentViewSet)
router.register(r'permissions', PermissionViewSet)
router.register(r'information-packages', InformationPackageViewSet)
router.register(r'information-packages', InformationPackageViewSet).register(
    r'events',
    EventIPViewSet,
    base_name='ip-events',
    parents_query_lookups=['linkingObjectIdentifierValue']
)
router.register(r'information-packages', InformationPackageViewSet).register(
    r'profiles',
    InformationPackageProfileIPViewSet,
    base_name='ip-profiles',
    parents_query_lookups=['ip']
)
router.register(r'notifications', NotificationViewSet)
router.register(r'steps', ProcessStepViewSet)
router.register(r'steps', ProcessStepViewSet, base_name='steps').register(
    r'tasks',
    ProcessTaskViewSet,
    base_name='steps-tasks',
    parents_query_lookups=['processstep']
)
router.register(r'steps', ProcessStepViewSet, base_name='steps').register(
    r'children',
    ProcessViewSet,
    base_name='steps-children',
    parents_query_lookups=['processstep']
)
router.register(r'tasks', ProcessTaskViewSet)
router.register(r'tasks', ProcessTaskViewSet).register(
    r'validations',
    ValidationViewSet,
    base_name='task-validations',
    parents_query_lookups=['task']
)
router.register(r'events', EventIPViewSet)
router.register(r'event-types', EventTypeViewSet)
router.register(r'submission-agreements', SubmissionAgreementViewSet)
router.register(r'profiles', ProfileViewSet)
router.register(r'profile-sa', ProfileSAViewSet)
router.register(r'profile-ip', ProfileIPViewSet)
router.register(r'profile-ip-data', ProfileIPDataViewSet)
router.register(r'profile-ip-data-templates', ProfileIPDataTemplateViewSet)
router.register(r'parameters', ParameterViewSet)
router.register(r'paths', PathViewSet)

router.register(r'orders', OrderViewSet)

router.register(r'appraisal-rules', AppraisalRuleViewSet)
router.register(r'appraisal-jobs', AppraisalJobViewSet)
router.register(r'conversion-jobs', ConversionJobViewSet)
router.register(r'workarea-entries', WorkareaEntryViewSet, base_name='workarea-entries')
router.register(r'workareas', WorkareaViewSet, base_name='workarea')
router.register(r'workareas', WorkareaViewSet, base_name='workarea').register(
    r'events',
    EventIPViewSet,
    base_name='workarea-events',
    parents_query_lookups=['linkingObjectIdentifierValue']
)
router.register(r'workarea-files', WorkareaFilesViewSet, base_name='workarea-files')

router.register(r'ip-reception', InformationPackageReceptionViewSet, base_name="ip-reception")

urlpatterns = [
    url(r'^', include('ESSArch_Core.frontend.urls'), name='home'),
    url(r'^admin/', admin.site.urls),
    url(r'^api/site/', SiteView.as_view()),
    url(r'^api/stats/$', stats),
    url(r'^api/stats/export/$', export_stats),
    url(r'^api/sysinfo/', SysInfoView.as_view()),
    url(r'^api/me/$', MeView.as_view(), name='me'),
    url(r'^api/', include(router.urls)),
    url(r'^accounts/changepassword', auth_views.PasswordChangeView.as_view(), {'post_change_redirect': '/'}),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^docs/', include('ESSArch_Core.docs.urls')),
    url(r'^template/', include('ESSArch_Core.essxml.ProfileMaker.urls')),
    url(r'^accounts/login/$', auth_views.LoginView.as_view()),
    url(r'^rest-auth/', include('ESSArch_Core.auth.urls')),
    url(r'^rest-auth/registration/', include('rest_auth.registration.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
