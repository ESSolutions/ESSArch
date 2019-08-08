from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views

from ESSArch_Core.auth.views import (
    GroupViewSet,
    MeView,
    NotificationViewSet,
    OrganizationViewSet,
    PermissionViewSet,
    UserViewSet,
)
from ESSArch_Core.configuration.views import (
    EventTypeViewSet,
    ParameterViewSet,
    PathViewSet,
    SiteView,
    StoragePolicyViewSet,
    SysInfoView,
)
from ESSArch_Core.fixity.views import ValidationFilesViewSet, ValidationViewSet
from ESSArch_Core.ip.views import (
    AgentViewSet,
    EventIPViewSet,
    InformationPackageReceptionViewSet,
    InformationPackageViewSet,
    OrderViewSet,
    WorkareaEntryViewSet,
    WorkareaFilesViewSet,
    WorkareaViewSet,
)
from ESSArch_Core.maintenance.views import (
    AppraisalJobViewSet,
    AppraisalRuleViewSet,
    ConversionJobViewSet,
    ConversionRuleViewSet,
)
from ESSArch_Core.profiles.views import (
    InformationPackageProfileIPViewSet,
    ProfileIPDataTemplateViewSet,
    ProfileIPDataViewSet,
    ProfileIPViewSet,
    ProfileMakerExtensionViewSet,
    ProfileMakerTemplateViewSet,
    ProfileSAViewSet,
    ProfileViewSet,
    SubmissionAgreementTemplateView,
    SubmissionAgreementViewSet,
)
from ESSArch_Core.routers import ESSArchRouter
from ESSArch_Core.stats.views import export as export_stats, stats
from ESSArch_Core.storage.views import (
    IOQueueViewSet,
    RobotQueueViewSet,
    RobotViewSet,
    StorageMediumViewSet,
    StorageMethodTargetRelationViewSet,
    StorageMethodViewSet,
    StorageObjectViewSet,
    StorageTargetViewSet,
    TapeDriveViewSet,
    TapeSlotViewSet,
)
from ESSArch_Core.tags.search import ComponentSearchViewSet
from ESSArch_Core.tags.views import TagInformationPackagesViewSet, TagViewSet
from ESSArch_Core.WorkflowEngine.views import (
    ProcessStepViewSet,
    ProcessTaskViewSet,
    ProcessViewSet,
)

admin.site.site_header = 'ESSArch Administration'
admin.site.site_title = 'ESSArch Administration'

router = ESSArchRouter()
router.register(r'users', UserViewSet)
router.register(r'groups', GroupViewSet)
router.register(r'agents', AgentViewSet)
router.register(r'permissions', PermissionViewSet)
router.register(r'profilemaker-extensions', ProfileMakerExtensionViewSet)
router.register(r'profilemaker-templates', ProfileMakerTemplateViewSet)
router.register(r'information-packages', InformationPackageViewSet, basename='informationpackage')
router.register(r'information-packages', InformationPackageViewSet).register(
    r'appraisal-rules',
    AppraisalRuleViewSet,
    basename='ip-appraisal-rules',
    parents_query_lookups=['information_packages']
)
router.register(r'information-packages', InformationPackageViewSet).register(
    r'conversion-rules',
    ConversionRuleViewSet,
    basename='ip-conversion-rules',
    parents_query_lookups=['information_packages']
)
router.register(r'information-packages', InformationPackageViewSet).register(
    r'events',
    EventIPViewSet,
    basename='ip-events',
    parents_query_lookups=['linkingObjectIdentifierValue']
)
router.register(r'information-packages', InformationPackageViewSet).register(
    r'profiles',
    InformationPackageProfileIPViewSet,
    basename='ip-profiles',
    parents_query_lookups=['ip']
)
router.register(r'information-packages', InformationPackageViewSet).register(
    r'storage-objects',
    StorageObjectViewSet,
    basename='ip-storage-objects',
    parents_query_lookups=['ip']
)
router.register(r'information-packages', InformationPackageViewSet).register(
    r'validations',
    ValidationViewSet,
    basename='ip-validations',
    parents_query_lookups=['information_package']
)
router.register(r'information-packages', InformationPackageViewSet).register(
    r'validation-files',
    ValidationFilesViewSet,
    basename='ip-validation-files',
    parents_query_lookups=['information_package']
)

router.register(r'io-queue', IOQueueViewSet)

router.register(r'notifications', NotificationViewSet)
router.register(r'steps', ProcessStepViewSet)
router.register(r'steps', ProcessStepViewSet, basename='steps').register(
    r'tasks',
    ProcessTaskViewSet,
    basename='steps-tasks',
    parents_query_lookups=['processstep']
)
router.register(r'steps', ProcessStepViewSet, basename='steps').register(
    r'children',
    ProcessViewSet,
    basename='steps-children',
    parents_query_lookups=['processstep']
)

router.register(r'tags', TagViewSet)
router.register(r'tags', TagViewSet, basename='tags').register(
    r'information-packages',
    TagInformationPackagesViewSet,
    basename='tags-informationpackages',
    parents_query_lookups=['tag']
)
router.register(r'tags', TagViewSet, basename='tags').register(
    r'descendants',
    TagViewSet,
    basename='tags-descendants',
    parents_query_lookups=['tag']
)

router.register(r'tasks', ProcessTaskViewSet)
router.register(r'tasks', ProcessTaskViewSet).register(
    r'validations',
    ValidationViewSet,
    basename='task-validations',
    parents_query_lookups=['task']
)


router.register(r'organizations', OrganizationViewSet, basename='organizations')
router.register(r'appraisal-jobs', AppraisalJobViewSet)
router.register(r'appraisal-rules', AppraisalRuleViewSet)
router.register(r'conversion-jobs', ConversionJobViewSet)
router.register(r'conversion-rules', ConversionRuleViewSet)
router.register(r'validations', ValidationViewSet)
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

router.register(r'storage-objects', StorageObjectViewSet)
router.register(r'storage-mediums', StorageMediumViewSet)
router.register(r'storage-methods', StorageMethodViewSet)
router.register(r'storage-method-target-relations', StorageMethodTargetRelationViewSet)
router.register(r'storage-policies', StoragePolicyViewSet)
router.register(r'storage-targets', StorageTargetViewSet)
router.register(r'tape-drives', TapeDriveViewSet)
router.register(r'tape-slots', TapeSlotViewSet)


router.register(r'storage-mediums', StorageMediumViewSet, basename='storagemedium').register(
    r'storage-objects',
    StorageObjectViewSet,
    basename='storagemedium-storageobject',
    parents_query_lookups=['storage_medium']
)

router.register(r'orders', OrderViewSet)

router.register(r'workarea-entries', WorkareaEntryViewSet, basename='workarea-entries')
router.register(r'workareas', WorkareaViewSet, basename='workarea')
router.register(r'workareas', WorkareaViewSet, basename='workarea').register(
    r'events',
    EventIPViewSet,
    basename='workarea-events',
    parents_query_lookups=['linkingObjectIdentifierValue']
)
router.register(r'workarea-files', WorkareaFilesViewSet, basename='workarea-files')


router.register(r'robots', RobotViewSet)
router.register(r'robots', ProcessStepViewSet, basename='robots').register(
    r'queue',
    RobotQueueViewSet,
    basename='robots-queue',
    parents_query_lookups=['robot']
)
router.register(r'robot-queue', RobotQueueViewSet)

router.register(r'robots', RobotViewSet, basename='robots').register(
    r'tape-slots',
    TapeSlotViewSet,
    basename='robots-tapeslots',
    parents_query_lookups=['tape_slots']
)
router.register(r'robots', RobotViewSet, basename='robots').register(
    r'tape-drives',
    TapeDriveViewSet,
    basename='robots-tapedrives',
    parents_query_lookups=['tape_drives']
)

router.register(r'ip-reception', InformationPackageReceptionViewSet, basename="ip-reception")

router.register(r'search', ComponentSearchViewSet, basename='search')

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
    url(r'^api/submission-agreement-template/$', SubmissionAgreementTemplateView.as_view()),
    url(r'^docs/', include('ESSArch_Core.docs.urls')),
    url(r'^template/', include('ESSArch_Core.essxml.ProfileMaker.urls')),
    url(r'^accounts/login/$', auth_views.LoginView.as_view()),
    url(r'^rest-auth/', include('ESSArch_Core.auth.urls')),
    url(r'^rest-auth/registration/', include('rest_auth.registration.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
