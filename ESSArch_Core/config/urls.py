from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic.base import RedirectView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from ESSArch_Core.access.views import AccessAidTypeViewSet, AccessAidViewSet
from ESSArch_Core.agents.views import (
    AgentIdentifierTypeViewSet,
    AgentNameTypeViewSet,
    AgentNoteTypeViewSet,
    AgentPlaceTypeViewSet,
    AgentRelationTypeViewSet,
    AgentTagLinkRelationTypeViewSet,
    AgentTypeViewSet,
    AgentViewSet,
    AuthorityTypeViewSet,
    RefCodeViewSet,
)
from ESSArch_Core.api.views import LanguageViewSet
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
    FeatureViewSet,
    ParameterViewSet,
    PathViewSet,
    SiteView,
    StoragePolicyViewSet,
    SysInfoView,
)
from ESSArch_Core.fixity.views import (
    ActionToolViewSet,
    SaveActionToolViewSet,
    ValidationFilesViewSet,
    ValidationViewSet,
)
from ESSArch_Core.ip.views import (
    ConsignMethodViewSet,
    EventIPViewSet,
    InformationPackageReceptionViewSet,
    InformationPackageViewSet,
    OrderTypeViewSet,
    OrderViewSet,
    WorkareaEntryViewSet,
    WorkareaFilesViewSet,
    WorkareaViewSet,
)
from ESSArch_Core.maintenance.views import (
    AppraisalJobInformationPackageViewSet,
    AppraisalJobTagViewSet,
    AppraisalJobViewSet,
    AppraisalTemplateViewSet,
    ConversionJobInformationPackageViewSet,
    ConversionJobViewSet,
    ConversionTemplateViewSet,
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
    SubmissionAgreementIPDataViewSet,
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
    StorageMigrationPreviewDetailView,
    StorageMigrationPreviewView,
    StorageMigrationViewSet,
    StorageObjectViewSet,
    StorageTargetViewSet,
    TapeDriveViewSet,
    TapeSlotViewSet,
)
from ESSArch_Core.tags.search import ComponentSearchViewSet
from ESSArch_Core.tags.views import (
    ArchiveViewSet,
    DeliveryTypeViewSet,
    DeliveryViewSet,
    LocationFunctionTypeViewSet,
    LocationLevelTypeViewSet,
    LocationViewSet,
    MetricTypeViewSet,
    NodeIdentifierTypeViewSet,
    NodeNoteTypeViewSet,
    NodeRelationTypeViewSet,
    StoredSearchViewSet,
    StructureTypeViewSet,
    StructureUnitTypeViewSet,
    StructureUnitViewSet,
    StructureViewSet,
    TagInformationPackagesViewSet,
    TagVersionTypeViewSet,
    TagVersionViewSet,
    TagViewSet,
    TransferViewSet,
)
from ESSArch_Core.WorkflowEngine.views import (
    ProcessStepViewSet,
    ProcessTaskViewSet,
    ProcessViewSet,
)

admin.site.site_header = 'ESSArch Administration'
admin.site.site_title = 'ESSArch Administration'

schema_view = get_schema_view(
    openapi.Info(
        title="ESSArch API",
        default_version='v3',
        description="ESSArch REST-API documentation",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

router = ESSArchRouter()
router.register(r'users', UserViewSet)
router.register(r'groups', GroupViewSet)
router.register(r'agents', AgentViewSet).register(
    r'archives',
    ArchiveViewSet,
    basename='agent-archives',
    parents_query_lookups=['agent']
)
router.register(r'access-aids', AccessAidViewSet)
router.register(r'access-aids', AccessAidViewSet).register(
    r'structure-units',
    StructureUnitViewSet,
    basename='access-aids-structure-units',
    parents_query_lookups=['access_aids'],
)
router.register(r'access-aid-types', AccessAidTypeViewSet)
router.register(r'agent-types', AgentTypeViewSet)
router.register(r'agent-identifier-types', AgentIdentifierTypeViewSet)
router.register(r'agent-name-types', AgentNameTypeViewSet)
router.register(r'agent-note-types', AgentNoteTypeViewSet)
router.register(r'agent-place-types', AgentPlaceTypeViewSet)
router.register(r'agent-relation-types', AgentRelationTypeViewSet)
router.register(r'agent-tag-relation-types', AgentTagLinkRelationTypeViewSet)
router.register(r'authority-types', AuthorityTypeViewSet)
router.register(r'deliveries', DeliveryViewSet).register(
    r'transfers',
    TransferViewSet,
    basename='transfers',
    parents_query_lookups=['delivery']
)
router.register(r'deliveries', DeliveryViewSet).register(
    r'events',
    EventIPViewSet,
    basename='delivery-events',
    parents_query_lookups=['delivery'],
)
router.register(r'delivery-types', DeliveryTypeViewSet)
router.register(r'transfers', TransferViewSet).register(
    r'events',
    EventIPViewSet,
    basename='transfer-events',
    parents_query_lookups=['transfer'],
)
router.register(r'transfers', TransferViewSet).register(
    r'structure-units',
    StructureUnitViewSet,
    basename='transfer-structure-units',
    parents_query_lookups=['transfers'],
)
router.register(r'transfers', TransferViewSet).register(
    r'tags',
    TagVersionViewSet,
    basename='transfer-tags',
    parents_query_lookups=['transfers'],
)
router.register(r'structures', StructureViewSet).register(
    r'units',
    StructureUnitViewSet,
    basename='structure-units',
    parents_query_lookups=['structure']
)
router.register(r'structure-units', StructureUnitViewSet).register(
    r'access-aids',
    AccessAidViewSet,
    basename='structure-unit-access-aids',
    parents_query_lookups=['structure_units'],
)
router.register(r'structure-units', StructureUnitViewSet).register(
    r'transfers',
    TransferViewSet,
    basename='structure-unit-transfers',
    parents_query_lookups=['structure_units'],
)
router.register(r'structure-units', StructureUnitViewSet).register(
    r'deliveries',
    DeliveryViewSet,
    basename='structure-unit-deliveries',
    parents_query_lookups=['structure_units__delivery'],
)
router.register(r'structure-types', StructureTypeViewSet)
router.register(r'structure-unit-types', StructureUnitTypeViewSet)
router.register(r'node-relation-types', NodeRelationTypeViewSet)
router.register(r'node-identifier-types', NodeIdentifierTypeViewSet)
router.register(r'node-note-types', NodeNoteTypeViewSet)
router.register(r'locations', LocationViewSet).register(
    r'tags',
    TagVersionViewSet,
    basename='location-tags',
    parents_query_lookups=['location']
)
router.register(r'metric-types', MetricTypeViewSet)
router.register(r'location-level-types', LocationLevelTypeViewSet)
router.register(r'location-function-types', LocationFunctionTypeViewSet)
router.register(r'structure-units', StructureUnitViewSet)
router.register(r'tag-version-types', TagVersionTypeViewSet)

router.register(r'ref-codes', RefCodeViewSet)
router.register(r'languages', LanguageViewSet)
router.register(r'me/searches', StoredSearchViewSet)
router.register(r'permissions', PermissionViewSet)
router.register(r'profilemaker-extensions', ProfileMakerExtensionViewSet)
router.register(r'profilemaker-templates', ProfileMakerTemplateViewSet)
router.register(r'information-packages', InformationPackageViewSet, basename='informationpackage')
router.register(r'information-packages', InformationPackageViewSet).register(
    r'appraisal-templates',
    AppraisalTemplateViewSet,
    basename='ip-appraisal-templates',
    parents_query_lookups=['information_packages']
)
router.register(r'information-packages', InformationPackageViewSet).register(
    r'conversion-templates',
    ConversionTemplateViewSet,
    basename='ip-conversion-templates',
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

router.register(r'appraisal-jobs', AppraisalJobViewSet).register(
    r'information-packages',
    AppraisalJobInformationPackageViewSet,
    basename='appraisal-job-information-packages',
    parents_query_lookups=['appraisal_jobs'],
)
router.register(r'appraisal-jobs', AppraisalJobViewSet).register(
    r'tags',
    AppraisalJobTagViewSet,
    basename='appraisal-job-tags',
    parents_query_lookups=['appraisal_jobs'],
)


router.register(r'appraisal-templates', AppraisalTemplateViewSet)

router.register(r'conversion-jobs', ConversionJobViewSet).register(
    r'information-packages',
    ConversionJobInformationPackageViewSet,
    basename='conversion-job-information-packages',
    parents_query_lookups=['conversion_jobs'],
)
router.register(r'conversion-templates', ConversionTemplateViewSet)
router.register(r'action-tools', ActionToolViewSet)
router.register(r'save-action-tools', SaveActionToolViewSet)
router.register(r'features', FeatureViewSet, basename='features')
router.register(r'validations', ValidationViewSet)
router.register(r'events', EventIPViewSet)
router.register(r'event-types', EventTypeViewSet)
router.register(r'submission-agreements', SubmissionAgreementViewSet)
router.register(r'submission-agreement-ip-data', SubmissionAgreementIPDataViewSet)
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
router.register(r'storage-migrations', StorageMigrationViewSet, basename='storage-migrations')
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

router.register(r'consign-methods', ConsignMethodViewSet)
router.register(r'order-types', OrderTypeViewSet)
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
    parents_query_lookups=['robot_id']
)
router.register(r'robot-queue', RobotQueueViewSet)

router.register(r'robots', RobotViewSet, basename='robots').register(
    r'tape-slots',
    TapeSlotViewSet,
    basename='robots-tapeslots',
    parents_query_lookups=['robot_id']
)
router.register(r'robots', RobotViewSet, basename='robots').register(
    r'tape-drives',
    TapeDriveViewSet,
    basename='robots-tapedrives',
    parents_query_lookups=['robot_id']
)

router.register(r'ip-reception', InformationPackageReceptionViewSet, basename="ip-reception")

router.register(r'search', ComponentSearchViewSet, basename='search').register(
    r'transfers',
    TransferViewSet,
    basename='tags-transfers',
    parents_query_lookups=['tag_versions'],
)

urlpatterns = [
    re_path(r'^', include('ESSArch_Core.frontend.urls'), name='home'),
    re_path(r'^admin/', admin.site.urls),
    path('favicon.ico', RedirectView.as_view(url='/static/frontend/favicon.ico')),
    re_path(r'^api/auth/', include('ESSArch_Core.auth.urls')),
    re_path(r'^api/docs/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    re_path(r'^api/site/', SiteView.as_view(), name='configuration-site'),
    re_path(r'^api/stats/$', stats, name='stats'),
    re_path(r'^api/stats/export/$', export_stats, name='stats-export'),
    re_path(
        r'^api/storage-migrations-preview/$',
        StorageMigrationPreviewView.as_view(),
        name='storage-migrations-preview',
    ),
    path(
        'api/storage-migrations-preview/<uuid:pk>/',
        StorageMigrationPreviewDetailView.as_view(),
        name='storage-migrations-preview-detail',
    ),
    re_path(r'^api/sysinfo/', SysInfoView.as_view(), name='configuration-sysinfo'),
    re_path(r'^api/me/$', MeView.as_view(), name='me'),
    re_path(r'^api/', include(router.urls)),
    re_path(r'^rest-framework/', include('rest_framework.urls', namespace='rest_framework')),
    re_path(
        r'^api/submission-agreement-template/$',
        SubmissionAgreementTemplateView.as_view(),
        name='profiles-submission-agreement-template',
    ),
    re_path(r'^docs/', include('ESSArch_Core.docs.urls')),
    re_path(r'^template/', include('ESSArch_Core.essxml.ProfileMaker.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if getattr(settings, 'ENABLE_SSO_LOGIN', False) or getattr(settings, 'ENABLE_ADFS_LOGIN', False) or \
        getattr(settings, 'ENABLE_SAML2_METADATA', False):
    from djangosaml2.views import EchoAttributesView
    urlpatterns.append(re_path(r'^saml2/', include('djangosaml2.urls')))
    urlpatterns.append(re_path(r'^saml2test/', EchoAttributesView.as_view()))
