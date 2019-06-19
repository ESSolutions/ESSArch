import * as angular from 'angular';

import AccessCtrl from '../controllers/AccessCtrl';
import AccessIpCtrl from '../controllers/AccessIpCtrl';
import AdministrationCtrl from '../controllers/AdministrationCtrl';
import AppCtrl from '../controllers/AppCtrl';
import AppraisalCtrl from '../controllers/AppraisalCtrl';
import BaseCtrl from '../controllers/BaseCtrl';
import CollectContentCtrl from '../controllers/CollectContentCtrl';
import CombinedWorkareaCtrl from '../controllers/CombinedWorkareaCtrl';
import ConversionCtrl from '../controllers/ConversionCtrl';
import CreateDipCtrl from '../controllers/CreateDipCtrl';
import CreateSipCtrl from '../controllers/CreateSipCtrl';
import DataModalInstanceCtrl from '../controllers/DataModalInstanceCtrl';
import HeadCtrl from '../controllers/HeadCtrl';
import IngestCtrl from '../controllers/IngestCtrl';
import IpApprovalCtrl from '../controllers/IpApprovalCtrl';
import LanguageCtrl from '../controllers/LanguageCtrl';
import MediaInformationCtrl from '../controllers/MediaInformationCtrl';
import ModalInstanceCtrl from '../controllers/ModalInstanceCtrl';
import MyPageCtrl from '../controllers/MyPageCtrl';
import OrdersCtrl from '../controllers/OrdersCtrl';
import {organization, OrganizationCtrl} from '../controllers/OrganizationCtrl';
import QueuesCtrl from '../controllers/QueuesCtrl';
import PrepareIpCtrl from '../controllers/PrepareIpCtrl';
import PrepareSipCtrl from '../controllers/PrepareSipCtrl';
import ProfileManagerCtrl from '../controllers/ProfileManagerCtrl';
import ReceptionCtrl from '../controllers/ReceptionCtrl';
import RobotInformationCtrl from '../controllers/RobotInformationCtrl';
import SearchCtrl from '../controllers/SearchCtrl';
import StorageMaintenanceCtrl from '../controllers/StorageMaintenanceCtrl';
import StorageMigrationCtrl from '../controllers/StorageMigrationCtrl';
import TagsCtrl from '../controllers/TagsCtrl';
import TaskInfoModalInstanceCtrl from '../controllers/TaskInfoModalInstanceCtrl';
import UserDropdownCtrl from '../controllers/UserDropdownCtrl';
import UserSettingsCtrl from '../controllers/UserSettingsCtrl';
import UtilCtrl from '../controllers/UtilCtrl';
import VersionCtrl from '../controllers/VersionCtrl';
import WorkareaCtrl from '../controllers/WorkareaCtrl';

import {permission, uiPermission} from 'angular-permission';
import uiRouter from '@uirouter/angularjs';

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
    //ngJsTree,
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
  .controller('AdministrationCtrl', AdministrationCtrl)
  .controller('AppCtrl', ['$rootScope', '$scope', '$uibModal', '$log', 'PermPermissionStore', AppCtrl])
  .controller('BaseCtrl', [
    'vm',
    'ipSortString',
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
    BaseCtrl,
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
    ConversionCtrl,
  ])
  .controller('CreateDipCtrl', [
    'IP',
    'ArchivePolicy',
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
  .controller('HeadCtrl', ['$scope', '$rootScope', '$translate', '$state', '$transitions', HeadCtrl])
  .controller('IngestCtrl', IngestCtrl)
  .controller('IpApprovalCtrl', [
    '$scope',
    '$controller',
    '$rootScope',
    '$translate',
    'ContextMenuBase',
    IpApprovalCtrl,
  ])
  .controller('LanguageCtrl', ['appConfig', '$scope', '$http', '$translate', LanguageCtrl])
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
    ModalInstanceCtrl,
  ])
  .controller('MyPageCtrl', ['$scope', '$controller', MyPageCtrl])
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
    OrdersCtrl,
  ])
  .controller('OrganizationCtrl', ['$scope', 'Organization', OrganizationCtrl])
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
    PrepareSipCtrl,
  ])
  .controller('ReceptionCtrl', [
    'IPReception',
    'IP',
    'ArchivePolicy',
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
    '$transitions',
    ReceptionCtrl,
  ])
  .controller('SearchCtrl', [
    'Search',
    '$scope',
    '$http',
    '$rootScope',
    'appConfig',
    '$log',
    'Notifications',
    '$translate',
    '$uibModal',
    'PermPermissionStore',
    '$window',
    '$state',
    '$httpParamSerializer',
    '$stateParams',
    '$transitions',
    SearchCtrl,
  ])
  .controller('TagsCtrl', ['$scope', 'vm', '$http', 'appConfig', TagsCtrl])
  .controller('TaskInfoModalInstanceCtrl', ['$uibModalInstance', 'data', '$rootScope', TaskInfoModalInstanceCtrl])
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
    'ArchivePolicy',
    '$scope',
    '$controller',
    '$rootScope',
    '$cookies',
    '$stateParams',
    'appConfig',
    '$http',
    '$timeout',
    '$uibModal',
    '$log',
    '$sce',
    '$window',
    'Notifications',
    '$filter',
    '$interval',
    'Appraisal',
    '$translate',
    '$transitions',
    AppraisalCtrl,
  ])
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
    QueuesCtrl,
  ])
  .controller('StorageMigrationCtrl', ['$scope', StorageMigrationCtrl])
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
  .controller('VersionCtrl', ['$scope', '$window', '$anchorScroll', '$location', '$translate', 'Sysinfo', VersionCtrl])
  .factory('Organization', ['$rootScope', '$http', '$state', 'appConfig', 'myService', organization]).name;
