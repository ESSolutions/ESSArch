import * as angular from 'angular';

import AccessCtrl from '../controllers/AccessCtrl';
import AccessModalInstanceCtrl from '../controllers/AccessModalInstanceCtrl';
import AccessIpCtrl from '../controllers/AccessIpCtrl';
import AccessWorkareaCtrl from '../controllers/AccessWorkareaCtrl';
import AddNodeModalInstanceCtrl from '../controllers/AddNodeModalInstanceCtrl';
import AdministrationCtrl from '../controllers/AdministrationCtrl';
import AgentModalInstanceCtrl from '../controllers/AgentModalInstanceCtrl';
import AgentArchiveRelationModalInstanceCtrl from '../controllers/AgentArchiveRelationModalInstanceCtrl';
import AgentIdentifierModalInstanceCtrl from '../controllers/AgentIdentifierModalInstanceCtrl';
import AgentMandateModalInstanceCtrl from '../controllers/AgentMandateModalInstanceCtrl';
import AgentNameModalInstanceCtrl from '../controllers/AgentNameModalInstanceCtrl';
import AgentNoteModalInstanceCtrl from '../controllers/AgentNoteModalInstanceCtrl';
import AgentPlaceModalInstanceCtrl from '../controllers/AgentPlaceModalInstanceCtrl';
import AngularTreeCtrl from '../controllers/AngularTreeCtrl';
import NodeLocationModalInstanceCtrl from '../controllers/NodeLocationModalInstanceCtrl';
import NodeNoteModalInstanceCtrl from '../controllers/NodeNoteModalInstanceCtrl';
import AgentRelationModalInstanceCtrl from '../controllers/AgentRelationModalInstanceCtrl';
import AppCtrl from '../controllers/AppCtrl';
import AppraisalCtrl from '../controllers/AppraisalCtrl';
import AppraisalModalInstanceCtrl from '../controllers/AppraisalModalInstanceCtrl';
import ArchiveMaintenanceCtrl from '../controllers/ArchiveMaintenanceCtrl';
import ArchiveModalInstanceCtrl from '../controllers/ArchiveModalInstanceCtrl';
import BaseCtrl from '../controllers/BaseCtrl';
import ChangePasswordModalCtrl from '../controllers/ChangePasswordModalCtrl';
import ClassificationModalInstanceCtrl from '../controllers/ClassificationModalInstanceCtrl';
import CollectContentCtrl from '../controllers/CollectContentCtrl';
import CombinedWorkareaCtrl from '../controllers/CombinedWorkareaCtrl';
import ConversionCtrl from '../controllers/ConversionCtrl';
import ConversionModalInstanceCtrl from '../controllers/ConversionModalInstanceCtrl';
import ConfirmReceiveCtrl from '../controllers/ConfirmReceiveCtrl';
import CreateDipCtrl from '../controllers/CreateDipCtrl';
import CreateSipCtrl from '../controllers/CreateSipCtrl';
import DataModalInstanceCtrl from '../controllers/DataModalInstanceCtrl';
import DeliveryModalInstanceCtrl from '../controllers/DeliveryModalInstanceCtrl';
import DownloadDipModalInstanceCtrl from '../controllers/DownloadDipModalInstanceCtrl';
import EditNodeModalInstanceCtrl from '../controllers/EditNodeModalInstanceCtrl';
import EditStructureUnitModalInstanceCtrl from '../controllers/EditStructureUnitModalInstanceCtrl';
import ExportResultModalInstanceCtrl from '../controllers/ExportResultModalInstanceCtrl';
import EventModalInstanceCtrl from '../controllers/EventModalInstanceCtrl';
import HeadCtrl from '../controllers/HeadCtrl';
import IngestCtrl from '../controllers/IngestCtrl';
import IngestWorkareaCtrl from '../controllers/IngestWorkareaCtrl';
import IpApprovalCtrl from '../controllers/IpApprovalCtrl';
import IpInformationModalInstanceCtrl from '../controllers/IpInformationModalInstanceCtrl';
import LanguageCtrl from '../controllers/LanguageCtrl';
import LocationModalInstanceCtrl from '../controllers/LocationModalInstanceCtrl';
import ManagementCtrl from '../controllers/ManagementCtrl';
import MediaInformationCtrl from '../controllers/MediaInformationCtrl';
import ModalInstanceCtrl from '../controllers/ModalInstanceCtrl';
import MoveToApprovalModalInstanceCtrl from '../controllers/MoveToApprovalInstanceCtrl';
import MyPageCtrl from '../controllers/MyPageCtrl';
import NodeDeliveryModalInstanceCtrl from '../controllers/NodeDeliveryModalInstanceCtrl';
import NodeIdentifierModalInstanceCtrl from '../controllers/NodeIdentifierModalInstanceCtrl';
import NodeOrganizationModalInstanceCtrl from '../controllers/NodeOrganizationModalInstanceCtrl';
import NodeTransferModalInstanceCtrl from '../controllers/NodeTransferModalInstanceCtrl';
import OrderModalInstanceCtrl from '../controllers/OrderModalInstanceCtrl';
import OrdersCtrl from '../controllers/OrdersCtrl';
import {organization, OrganizationCtrl} from '../controllers/OrganizationCtrl';
import OrganizationModalInstanceCtrl from '../controllers/OrganizationModalInstanceCtrl';
import OverwriteModalInstanceCtrl from '../controllers/OverwriteModalInstanceCtrl';
import QueuesCtrl from '../controllers/QueuesCtrl';
import PlaceNodeInArchiveModalInstanceCtrl from '../controllers/PlaceNodeInArchiveModalInstanceCtrl';
import PrepareDipModalInstanceCtrl from '../controllers/PrepareDipModalInstanceCtrl';
import PrepareIpCtrl from '../controllers/PrepareIpCtrl';
import PrepareIpModalInstanceCtrl from '../controllers/PrepareIpModalInstanceCtrl';
import PrepareSipCtrl from '../controllers/PrepareSipCtrl';
import PreserveModalInstanceCtrl from '../controllers/PreserveModalInstanceCtrl';
import ProfileManagerCtrl from '../controllers/ProfileManagerCtrl';
import PublishClassificationStructureCtrl from '../controllers/PublishClassificationStructureCtrl';
import UnpublishClassificationStructureCtrl from '../controllers/UnpublishClassificationStructureCtrl';
import ReceiveModalInstanceCtrl from '../controllers/ReceiveModalInstanceCtrl';
import ReceptionCtrl from '../controllers/ReceptionCtrl';
import RemoveNodeModalInstanceCtrl from '../controllers/RemoveNodeModalInstanceCtrl';
import RemoveStructureModalInstanceCtrl from '../controllers/RemoveStructureModalInstanceCtrl';
import RemoveStructureUnitModalInstanceCtrl from '../controllers/RemoveStructureUnitModalInstanceCtrl';
import RequestModalInstanceCtrl from '../controllers/RequestModalInstanceCtrl';
import RestrictedCtrl from '../controllers/RestrictedCtrl';
import RobotInformationCtrl from '../controllers/RobotInformationCtrl';
import SavedSearchModalInstanceCtrl from '../controllers/SavedSearchModalInstanceCtrl';
import StatsReportModalInstanceCtrl from '../controllers/StatsReportModalInstanceCtrl';
import SearchCtrl from '../controllers/SearchCtrl';
import SearchDetailCtrl from '../controllers/SearchDetailCtrl';
import SearchIpCtrl from '../controllers/SearchIpCtrl';
import StepInfoModalInstanceCtrl from '../controllers/StepInfoModalInstanceCtrl';
import StorageMaintenanceCtrl from '../controllers/StorageMaintenanceCtrl';
import StorageMigrationCtrl from '../controllers/StorageMigrationCtrl';
import StorageMigrationModalInstanceCtrl from '../controllers/StorageMigrationModalInstanceCtrl';
import StorageMigrationPreviewModalInstanceCtrl from '../controllers/StorageMigrationPreviewModalInstanceCtrl';
import StructureModalInstanceCtrl from '../controllers/StructureModalInstanceCtrl';
import StructureRuleModalCtrl from '../controllers/StructureRuleModalCtrl';
import StructureUnitRelationModalInstanceCtrl from '../controllers/StructureUnitRelationModalInstanceCtrl';
import StructureVersionModalInstanceCtrl from '../controllers/StructureVersionModalInstanceCtrl';
import TagsCtrl from '../controllers/TagsCtrl';
import TaskInfoModalInstanceCtrl from '../controllers/TaskInfoModalInstanceCtrl';
import TransferCtrl from '../controllers/TransferCtrl';
import TemplateModalInstanceCtrl from '../controllers/TemplateModalInstanceCtrl';
import TransferModalInstanceCtrl from '../controllers/TransferModalInstanceCtrl';
import UserDropdownCtrl from '../controllers/UserDropdownCtrl';
import UserSettingsCtrl from '../controllers/UserSettingsCtrl';
import UtilCtrl from '../controllers/UtilCtrl';
import VersionCtrl from '../controllers/VersionCtrl';
import VersionModalInstanceCtrl from '../controllers/VersionModalInstanceCtrl';
import WorkareaCtrl from '../controllers/WorkareaCtrl';
import StateTreeCtrl from '../controllers/StateTreeCtrl';

import {permission, uiPermission} from 'angular-permission';
import uiRouter from '@uirouter/angularjs';

import 'jstree';
import 'ng-js-tree';

import '../configs/config.json';
import '../configs/permissions.json';

export default angular
  .module('essarch.controllers', [
    'angular-clipboard',
    'angular-cron-jobs',
    'angularResizable',
    'essarch.appConfig',
    'essarch.services',
    'flow',
    'formly',
    'formlyBootstrap',
    'hc.marked',
    'ig.linkHeaderParser',
    'ngAnimate',
    'ngCookies',
    'ngFilesizeFilter',
    'ngJsTree',
    'ngMessages',
    'ngResource',
    'ngSanitize',
    'ngWebSocket',
    'pascalprecht.translate',
    'permission.config',
    uiRouter,
    permission,
    uiPermission,
    'relativeDate',
    'smart-table',
    'treeControl',
    'treeGrid',
    'ui.bootstrap.contextMenu',
    'ui.bootstrap.datetimepicker',
    'ui.bootstrap',
    'ui.dateTimeInput',
    'ui.select',
  ])
  .controller('AccessCtrl', AccessCtrl)
  .controller('AccessModalInstanceCtrl', ['$uibModalInstance', 'data', 'Requests', '$q', AccessModalInstanceCtrl])
  .controller('AccessIpCtrl', [
    '$scope',
    '$controller',
    '$rootScope',
    '$translate',
    '$uibModal',
    '$log',
    'ContextMenuBase',
    '$transitions',
    AccessIpCtrl,
  ])
  .controller('AccessWorkareaCtrl', ['$scope', '$controller', AccessWorkareaCtrl])
  .controller('AddNodeModalInstanceCtrl', [
    'Search',
    '$translate',
    '$uibModalInstance',
    'appConfig',
    '$http',
    'data',
    '$scope',
    'Notifications',
    '$rootScope',
    'EditMode',
    AddNodeModalInstanceCtrl,
  ])
  .controller('AdministrationCtrl', AdministrationCtrl)
  .controller('AgentModalInstanceCtrl', [
    '$uibModalInstance',
    'appConfig',
    'data',
    '$http',
    'EditMode',
    '$scope',
    '$translate',
    '$rootScope',
    '$q',
    AgentModalInstanceCtrl,
  ])
  .controller('AgentArchiveRelationModalInstanceCtrl', [
    '$uibModalInstance',
    'appConfig',
    'data',
    '$http',
    'EditMode',
    '$scope',
    '$translate',
    '$filter',
    '$rootScope',
    AgentArchiveRelationModalInstanceCtrl,
  ])
  .controller('AgentIdentifierModalInstanceCtrl', [
    '$uibModalInstance',
    '$scope',
    '$translate',
    '$http',
    'appConfig',
    'data',
    'EditMode',
    '$rootScope',
    AgentIdentifierModalInstanceCtrl,
  ])
  .controller('AgentMandateModalInstanceCtrl', [
    '$uibModalInstance',
    '$scope',
    '$translate',
    '$http',
    'appConfig',
    'data',
    'EditMode',
    '$rootScope',
    AgentMandateModalInstanceCtrl,
  ])
  .controller('AgentNameModalInstanceCtrl', [
    '$uibModalInstance',
    '$scope',
    '$translate',
    '$http',
    'appConfig',
    'data',
    'EditMode',
    '$rootScope',
    AgentNameModalInstanceCtrl,
  ])
  .controller('AgentNoteModalInstanceCtrl', [
    '$uibModalInstance',
    '$scope',
    '$translate',
    '$http',
    'appConfig',
    'data',
    'EditMode',
    '$rootScope',
    AgentNoteModalInstanceCtrl,
  ])
  .controller('AgentPlaceModalInstanceCtrl', [
    '$uibModalInstance',
    '$scope',
    '$translate',
    '$http',
    'appConfig',
    'data',
    'EditMode',
    '$rootScope',
    AgentPlaceModalInstanceCtrl,
  ])
  .controller('AgentRelationModalInstanceCtrl', [
    '$uibModalInstance',
    'appConfig',
    'data',
    '$http',
    'EditMode',
    '$scope',
    '$translate',
    'AgentName',
    '$rootScope',
    AgentRelationModalInstanceCtrl,
  ])
  .controller('AngularTreeCtrl', [
    'Tag',
    '$scope',
    '$rootScope',
    '$translate',
    '$uibModal',
    '$log',
    '$state',
    AngularTreeCtrl,
  ])
  .controller('AppCtrl', ['$rootScope', '$scope', '$uibModal', '$log', 'PermPermissionStore', '$translate', AppCtrl])
  .controller('AppraisalModalInstanceCtrl', [
    'cronService',
    '$filter',
    '$translate',
    'IP',
    '$uibModalInstance',
    'appConfig',
    '$http',
    'data',
    'Notifications',
    AppraisalModalInstanceCtrl,
  ])
  .controller('ArchiveMaintenanceCtrl', [ArchiveMaintenanceCtrl])
  .controller('ArchiveModalInstanceCtrl', [
    'Search',
    '$translate',
    '$uibModalInstance',
    'appConfig',
    '$http',
    'data',
    'Notifications',
    'AgentName',
    'EditMode',
    '$scope',
    '$rootScope',
    'Utils',
    'StructureName',
    '$q',
    ArchiveModalInstanceCtrl,
  ])
  .controller('BaseCtrl', [
    'vm',
    'ipSortString',
    'params',
    '$log',
    '$uibModal',
    '$timeout',
    '$scope',
    '$window',
    '$http',
    'appConfig',
    '$state',
    '$rootScope',
    'listViewService',
    '$interval',
    'Resource',
    '$translate',
    '$cookies',
    'PermPermissionStore',
    'Requests',
    'ContentTabs',
    'SelectedIPUpdater',
    '$transitions',
    '$stateParams',
    '$q',
    'Filters',
    BaseCtrl,
  ])
  .controller('ChangePasswordModalCtrl', ['$uibModalInstance', 'djangoAuth', 'data', ChangePasswordModalCtrl])
  .controller('ClassificationModalInstanceCtrl', [
    'data',
    '$http',
    'appConfig',
    'Notifications',
    '$uibModalInstance',
    '$translate',
    'Structure',
    'EditMode',
    '$scope',
    '$rootScope',
    ClassificationModalInstanceCtrl,
  ])
  .controller('CollectContentCtrl', [
    'IP',
    '$log',
    '$uibModal',
    '$timeout',
    '$scope',
    '$rootScope',
    '$window',
    'appConfig',
    'listViewService',
    '$interval',
    '$anchorScroll',
    '$cookies',
    '$controller',
    '$transitions',
    '$state',
    '$translate',
    CollectContentCtrl,
  ])
  .controller('CombinedWorkareaCtrl', ['$scope', '$controller', CombinedWorkareaCtrl])
  .controller('ConversionCtrl', [
    '$scope',
    'appConfig',
    '$http',
    '$uibModal',
    '$log',
    '$sce',
    '$window',
    'Notifications',
    '$interval',
    'Conversion',
    '$translate',
    '$transitions',
    'listViewService',
    ConversionCtrl,
  ])
  .controller('ConversionModalInstanceCtrl', [
    'cronService',
    '$filter',
    '$translate',
    'IP',
    '$uibModalInstance',
    'appConfig',
    '$http',
    'data',
    'Notifications',
    ConversionModalInstanceCtrl,
  ])
  .controller('ConfirmReceiveCtrl', ['IPReception', 'Notifications', '$uibModalInstance', 'data', ConfirmReceiveCtrl])
  .controller('CreateDipCtrl', [
    'IP',
    'StoragePolicy',
    '$scope',
    '$rootScope',
    '$state',
    '$controller',
    '$cookies',
    '$http',
    '$interval',
    'appConfig',
    '$timeout',
    '$anchorScroll',
    '$uibModal',
    '$translate',
    'listViewService',
    'Resource',
    '$sce',
    '$window',
    'ContextMenuBase',
    'SelectedIPUpdater',
    '$transitions',
    CreateDipCtrl,
  ])
  .controller('CreateSipCtrl', [
    'Profile',
    '$log',
    '$scope',
    '$rootScope',
    '$state',
    '$uibModal',
    '$anchorScroll',
    '$controller',
    '$translate',
    CreateSipCtrl,
  ])
  .controller('DataModalInstanceCtrl', [
    'IP',
    '$scope',
    '$uibModalInstance',
    'Notifications',
    'data',
    '$q',
    DataModalInstanceCtrl,
  ])
  .controller('DeliveryModalInstanceCtrl', [
    'appConfig',
    '$http',
    '$translate',
    'data',
    '$uibModalInstance',
    '$scope',
    'EditMode',
    'Utils',
    '$rootScope',
    'AgentName',
    DeliveryModalInstanceCtrl,
  ])
  .controller('DownloadDipModalInstanceCtrl', [
    '$uibModalInstance',
    'data',
    'appConfig',
    '$window',
    '$sce',
    DownloadDipModalInstanceCtrl,
  ])
  .controller('EditNodeModalInstanceCtrl', [
    'Search',
    '$translate',
    '$uibModalInstance',
    '$scope',
    'appConfig',
    '$http',
    'data',
    'Notifications',
    'EditMode',
    '$rootScope',
    EditNodeModalInstanceCtrl,
  ])
  .controller('EditStructureUnitModalInstanceCtrl', [
    '$translate',
    '$uibModalInstance',
    'appConfig',
    '$http',
    'data',
    '$scope',
    'Notifications',
    'EditMode',
    '$rootScope',
    EditStructureUnitModalInstanceCtrl,
  ])
  .controller('EventModalInstanceCtrl', [
    'appConfig',
    '$http',
    '$translate',
    'data',
    '$uibModalInstance',
    '$scope',
    'EditMode',
    'Utils',
    '$rootScope',
    EventModalInstanceCtrl,
  ])
  .controller('ExportResultModalInstanceCtrl', [
    '$uibModalInstance',
    'data',
    '$sce',
    '$window',
    ExportResultModalInstanceCtrl,
  ])
  .controller('HeadCtrl', ['$scope', '$rootScope', '$translate', '$state', '$transitions', HeadCtrl])
  .controller('IngestCtrl', IngestCtrl)
  .controller('IngestWorkareaCtrl', ['$scope', '$controller', IngestWorkareaCtrl])
  .controller('IpApprovalCtrl', [
    '$scope',
    '$controller',
    '$rootScope',
    '$translate',
    'ContextMenuBase',
    IpApprovalCtrl,
  ])
  .controller('IpInformationModalInstanceCtrl', [
    'IP',
    '$uibModalInstance',
    'data',
    '$scope',
    'Notifications',
    IpInformationModalInstanceCtrl,
  ])
  .controller('LanguageCtrl', ['appConfig', '$http', '$translate', LanguageCtrl])
  .controller('MediaInformationCtrl', [
    '$scope',
    '$rootScope',
    '$controller',
    'appConfig',
    'Resource',
    '$interval',
    'SelectedIPUpdater',
    'listViewService',
    '$transitions',
    MediaInformationCtrl,
  ])
  .controller('LocationModalInstanceCtrl', [
    '$scope',
    '$http',
    'appConfig',
    '$translate',
    'data',
    '$uibModalInstance',
    '$q',
    'EditMode',
    'Utils',
    '$rootScope',
    LocationModalInstanceCtrl,
  ])
  .controller('ManagementCtrl', [ManagementCtrl])
  .controller('ModalInstanceCtrl', [
    '$uibModalInstance',
    'djangoAuth',
    'data',
    '$http',
    'Notifications',
    'IP',
    'appConfig',
    'listViewService',
    '$translate',
    '$rootScope',
    ModalInstanceCtrl,
  ])
  .controller('MoveToApprovalModalInstanceCtrl', [
    '$uibModalInstance',
    'data',
    'Requests',
    '$q',
    MoveToApprovalModalInstanceCtrl,
  ])
  .controller('NodeDeliveryModalInstanceCtrl', [
    'appConfig',
    '$http',
    '$translate',
    'data',
    '$uibModalInstance',
    '$scope',
    'EditMode',
    '$rootScope',
    '$q',
    'Notifications',
    NodeDeliveryModalInstanceCtrl,
  ])
  .controller('NodeIdentifierModalInstanceCtrl', [
    '$uibModalInstance',
    '$scope',
    '$translate',
    '$http',
    'appConfig',
    'data',
    'EditMode',
    '$rootScope',
    NodeIdentifierModalInstanceCtrl,
  ])
  .controller('NodeLocationModalInstanceCtrl', [
    '$scope',
    'data',
    '$uibModalInstance',
    'EditMode',
    'Search',
    '$translate',
    '$q',
    'Notifications',
    NodeLocationModalInstanceCtrl,
  ])
  .controller('NodeNoteModalInstanceCtrl', [
    '$uibModalInstance',
    '$scope',
    '$translate',
    '$http',
    'appConfig',
    'data',
    'EditMode',
    '$rootScope',
    NodeNoteModalInstanceCtrl,
  ])
  .controller('NodeOrganizationModalInstanceCtrl', [
    '$translate',
    '$uibModalInstance',
    'appConfig',
    '$http',
    'data',
    'Notifications',
    'Organization',
    NodeOrganizationModalInstanceCtrl,
  ])
  .controller('NodeTransferModalInstanceCtrl', [
    '$scope',
    'data',
    '$uibModalInstance',
    'appConfig',
    '$http',
    'EditMode',
    '$translate',
    NodeTransferModalInstanceCtrl,
  ])
  .controller('MyPageCtrl', ['$scope', MyPageCtrl])
  .controller('OrderModalInstanceCtrl', [
    '$uibModalInstance',
    'data',
    '$http',
    'appConfig',
    'listViewService',
    '$translate',
    'Utils',
    '$q',
    'EditMode',
    '$scope',
    '$window',
    '$sce',
    OrderModalInstanceCtrl,
  ])
  .controller('OrdersCtrl', [
    '$scope',
    '$controller',
    '$rootScope',
    'Resource',
    '$timeout',
    'appConfig',
    '$http',
    '$uibModal',
    '$q',
    '$log',
    'SelectedIPUpdater',
    'listViewService',
    '$state',
    'myService',
    OrdersCtrl,
  ])
  .controller('OrganizationCtrl', ['$scope', 'Organization', OrganizationCtrl])
  .controller('OrganizationModalInstanceCtrl', [
    '$translate',
    '$uibModalInstance',
    'appConfig',
    '$http',
    'data',
    'Notifications',
    'Organization',
    OrganizationModalInstanceCtrl,
  ])
  .controller('OverwriteModalInstanceCtrl', [
    '$uibModalInstance',
    'data',
    'Profile',
    'SA',
    'Notifications',
    '$translate',
    OverwriteModalInstanceCtrl,
  ])
  .controller('PlaceNodeInArchiveModalInstanceCtrl', [
    '$uibModalInstance',
    '$scope',
    '$translate',
    '$http',
    'appConfig',
    'data',
    'EditMode',
    'StructureName',
    PlaceNodeInArchiveModalInstanceCtrl,
  ])
  .controller('ProfileManagerCtrl', ['$state', '$scope', ProfileManagerCtrl])
  .controller('PrepareIpCtrl', [
    'IP',
    'SA',
    'Profile',
    '$log',
    '$uibModal',
    '$timeout',
    '$scope',
    '$rootScope',
    'listViewService',
    '$translate',
    '$controller',
    PrepareIpCtrl,
  ])
  .controller('PrepareDipModalInstanceCtrl', [
    '$uibModalInstance',
    'data',
    '$http',
    'appConfig',
    '$q',
    'IP',
    PrepareDipModalInstanceCtrl,
  ])
  .controller('PrepareIpModalInstanceCtrl', [
    '$uibModalInstance',
    'data',
    'IP',
    'EditMode',
    '$scope',
    '$translate',
    PrepareIpModalInstanceCtrl,
  ])
  .controller('PrepareSipCtrl', [
    'Profile',
    '$log',
    '$uibModal',
    '$scope',
    '$rootScope',
    '$http',
    'appConfig',
    'listViewService',
    '$anchorScroll',
    '$controller',
    '$timeout',
    '$state',
    'ContentTabs',
    '$translate',
    PrepareSipCtrl,
  ])
  .controller('PublishClassificationStructureCtrl', [
    '$http',
    'appConfig',
    '$uibModalInstance',
    'data',
    '$rootScope',
    PublishClassificationStructureCtrl,
  ])
  .controller('UnpublishClassificationStructureCtrl', [
    '$http',
    'appConfig',
    '$uibModalInstance',
    'data',
    '$rootScope',
    UnpublishClassificationStructureCtrl,
  ])
  .controller('ReceiveModalInstanceCtrl', [
    '$uibModalInstance',
    '$scope',
    'data',
    '$translate',
    '$uibModal',
    '$log',
    '$http',
    'appConfig',
    '$q',
    'EditMode',
    ReceiveModalInstanceCtrl,
  ])
  .controller('ReceptionCtrl', [
    'IPReception',
    'IP',
    'StoragePolicy',
    '$log',
    '$uibModal',
    '$scope',
    'appConfig',
    '$state',
    '$rootScope',
    'listViewService',
    'Resource',
    '$translate',
    '$controller',
    'ContextMenuBase',
    'SelectedIPUpdater',
    '$filter',
    '$transitions',
    ReceptionCtrl,
  ])
  .controller('RemoveNodeModalInstanceCtrl', [
    'Search',
    '$translate',
    '$uibModalInstance',
    'data',
    'Notifications',
    '$rootScope',
    RemoveNodeModalInstanceCtrl,
  ])
  .controller('RemoveStructureModalInstanceCtrl', [
    'data',
    'Notifications',
    '$uibModalInstance',
    '$translate',
    'Structure',
    RemoveStructureModalInstanceCtrl,
  ])
  .controller('RemoveStructureUnitModalInstanceCtrl', [
    'data',
    '$http',
    'appConfig',
    'Notifications',
    '$uibModalInstance',
    '$translate',
    RemoveStructureUnitModalInstanceCtrl,
  ])
  .controller('RestrictedCtrl', ['$scope', RestrictedCtrl])
  .controller('SavedSearchModalInstanceCtrl', [
    '$uibModalInstance',
    'appConfig',
    '$http',
    'data',
    SavedSearchModalInstanceCtrl,
  ])
  .controller('SearchCtrl', [
    'Search',
    '$scope',
    '$http',
    '$rootScope',
    'appConfig',
    '$log',
    '$timeout',
    'Notifications',
    '$translate',
    '$uibModal',
    'PermPermissionStore',
    '$window',
    '$state',
    '$httpParamSerializer',
    '$stateParams',
    '$transitions',
    'AgentName',
    SearchCtrl,
  ])
  .controller('SearchDetailCtrl', [
    '$scope',
    '$controller',
    '$stateParams',
    'Search',
    '$q',
    '$http',
    '$rootScope',
    'appConfig',
    '$log',
    'Notifications',
    '$sce',
    '$translate',
    '$uibModal',
    'PermPermissionStore',
    '$window',
    '$state',
    '$interval',
    'StructureName',
    'AgentName',
    '$transitions',
    'StructureUnitRelation',
    SearchDetailCtrl,
  ])
  .controller('SearchIpCtrl', [
    'appConfig',
    '$rootScope',
    '$http',
    'IP',
    '$stateParams',
    'Notifications',
    '$state',
    SearchIpCtrl,
  ])
  .controller('StructureModalInstanceCtrl', [
    'Search',
    '$translate',
    '$uibModalInstance',
    'data',
    'Notifications',
    StructureModalInstanceCtrl,
  ])
  .controller('StructureRuleModalCtrl', [
    '$uibModalInstance',
    '$http',
    'appConfig',
    'data',
    'EditMode',
    '$q',
    '$translate',
    'Structure',
    'Notifications',
    StructureRuleModalCtrl,
  ])
  .controller('StructureUnitRelationModalInstanceCtrl', [
    '$uibModalInstance',
    'appConfig',
    'data',
    '$http',
    'EditMode',
    '$translate',
    '$scope',
    '$rootScope',
    'StructureName',
    '$timeout',
    StructureUnitRelationModalInstanceCtrl,
  ])
  .controller('StructureVersionModalInstanceCtrl', [
    '$translate',
    '$uibModalInstance',
    'appConfig',
    '$http',
    'data',
    'Notifications',
    StructureVersionModalInstanceCtrl,
  ])
  .controller('TagsCtrl', ['$scope', 'vm', '$http', 'appConfig', TagsCtrl])
  .controller('TransferCtrl', [
    '$scope',
    'appConfig',
    '$http',
    '$uibModal',
    '$log',
    '$translate',
    'myService',
    '$state',
    '$stateParams',
    'listViewService',
    '$transitions',
    TransferCtrl,
  ])
  .controller('TransferModalInstanceCtrl', [
    'appConfig',
    '$http',
    '$translate',
    'data',
    '$uibModalInstance',
    '$scope',
    'EditMode',
    'Utils',
    '$rootScope',
    TransferModalInstanceCtrl,
  ])
  .controller('StepInfoModalInstanceCtrl', [
    '$uibModalInstance',
    'data',
    '$rootScope',
    '$scope',
    'PermPermissionStore',
    'Step',
    '$uibModal',
    StepInfoModalInstanceCtrl,
  ])
  .controller('TaskInfoModalInstanceCtrl', [
    '$uibModalInstance',
    'data',
    '$rootScope',
    '$scope',
    'PermPermissionStore',
    'Task',
    'listViewService',
    '$uibModal',
    '$timeout',
    TaskInfoModalInstanceCtrl,
  ])
  .controller('UserDropdownCtrl', [
    '$scope',
    '$log',
    '$state',
    'djangoAuth',
    '$translate',
    '$uibModal',
    UserDropdownCtrl,
  ])
  .controller('UserSettingsCtrl', [
    'Me',
    '$scope',
    '$rootScope',
    '$controller',
    'myService',
    '$window',
    UserSettingsCtrl,
  ])
  .controller('UtilCtrl', [
    'Notifications',
    '$scope',
    '$state',
    '$timeout',
    'myService',
    'permissionConfig',
    '$anchorScroll',
    '$transitions',
    '$window',
    '$translate',
    UtilCtrl,
  ])
  .controller('AppraisalCtrl', [
    '$scope',
    'appConfig',
    '$http',
    '$uibModal',
    '$log',
    '$sce',
    '$window',
    'Notifications',
    '$interval',
    'Appraisal',
    '$translate',
    '$transitions',
    'listViewService',
    AppraisalCtrl,
  ])
  .controller('RequestModalInstanceCtrl', ['$uibModalInstance', 'data', '$scope', RequestModalInstanceCtrl])
  .controller('RobotInformationCtrl', [
    'StorageMedium',
    '$scope',
    '$controller',
    '$interval',
    '$rootScope',
    '$http',
    'Resource',
    'appConfig',
    '$timeout',
    '$anchorScroll',
    '$translate',
    'Storage',
    '$uibModal',
    'listViewService',
    '$transitions',
    RobotInformationCtrl,
  ])
  .controller('QueuesCtrl', [
    'appConfig',
    '$scope',
    '$rootScope',
    'Storage',
    'Resource',
    '$interval',
    '$transitions',
    'listViewService',
    QueuesCtrl,
  ])
  .controller('StatsReportModalInstanceCtrl', [
    '$uibModalInstance',
    'appConfig',
    'data',
    '$sce',
    '$window',
    StatsReportModalInstanceCtrl,
  ])
  .controller('StateTreeCtrl', [
    '$scope',
    '$translate',
    'Step',
    'Task',
    'appConfig',
    '$timeout',
    '$interval',
    'PermPermissionStore',
    '$q',
    '$uibModal',
    '$log',
    'StateTree',
    '$rootScope',
    '$transitions',
    'listViewService',
    StateTreeCtrl,
  ])
  .controller('StorageMigrationCtrl', [
    '$rootScope',
    '$scope',
    'appConfig',
    '$http',
    'listViewService',
    'SelectedIPUpdater',
    '$controller',
    '$translate',
    '$uibModal',
    'StorageMedium',
    StorageMigrationCtrl,
  ])
  .controller('StorageMigrationModalInstanceCtrl', [
    '$uibModalInstance',
    'data',
    '$http',
    'appConfig',
    '$translate',
    '$log',
    'EditMode',
    '$scope',
    '$uibModal',
    StorageMigrationModalInstanceCtrl,
  ])
  .controller('StorageMigrationPreviewModalInstanceCtrl', [
    '$uibModalInstance',
    'data',
    '$http',
    'appConfig',
    '$translate',
    '$log',
    '$scope',
    StorageMigrationPreviewModalInstanceCtrl,
  ])
  .controller('StorageMaintenanceCtrl', ['$scope', '$rootScope', StorageMaintenanceCtrl])
  .controller('WorkareaCtrl', [
    'vm',
    'ipSortString',
    'WorkareaFiles',
    'Workarea',
    '$scope',
    '$controller',
    '$rootScope',
    'Resource',
    '$interval',
    '$timeout',
    'appConfig',
    '$cookies',
    '$anchorScroll',
    '$translate',
    '$state',
    '$http',
    'listViewService',
    'Requests',
    '$uibModal',
    '$sce',
    '$window',
    'ContextMenuBase',
    'SelectedIPUpdater',
    WorkareaCtrl,
  ])
  .controller('PreserveModalInstanceCtrl', ['$uibModalInstance', 'data', 'Requests', '$q', PreserveModalInstanceCtrl])
  .controller('TemplateModalInstanceCtrl', [
    'ProfileMakerTemplate',
    '$uibModalInstance',
    'data',
    TemplateModalInstanceCtrl,
  ])
  .controller('VersionCtrl', ['$scope', '$window', '$anchorScroll', '$location', '$translate', 'Sysinfo', VersionCtrl])
  .controller('VersionModalInstanceCtrl', [
    'Search',
    '$translate',
    '$uibModalInstance',
    'data',
    'Notifications',
    VersionModalInstanceCtrl,
  ])
  .factory('Organization', ['$rootScope', '$http', '$state', 'appConfig', 'myService', organization]).name;
