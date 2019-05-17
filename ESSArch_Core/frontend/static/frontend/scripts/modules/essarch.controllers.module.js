import AccessCtrl from '../controllers/AccessCtrl';
import AccessIpCtrl from '../controllers/AccessIpCtrl';
import AdministrationCtrl from '../controllers/AdministrationCtrl';
import AppCtrl from '../controllers/AppCtrl';
import BaseCtrl from '../controllers/BaseCtrl';
import CombinedWorkareaCtrl from '../controllers/CombinedWorkareaCtrl';
import ConversionCtrl from '../controllers/ConversionCtrl';
import CreateDipCtrl from '../controllers/CreateDipCtrl';
import HeadCtrl from '../controllers/HeadCtrl';
import IngestCtrl from '../controllers/IngestCtrl';
import IpApprovalCtrl from '../controllers/IpApprovalCtrl';
import LanguageCtrl from '../controllers/LanguageCtrl';
import MediaInformationCtrl from '../controllers/MediaInformationCtrl';
import MyPageCtrl from '../controllers/MyPageCtrl';
import OrdersCtrl from '../controllers/OrdersCtrl';
import {organization, OrganizationCtrl} from '../controllers/OrganizationCtrl';
import ProfileManagerCtrl from '../controllers/ProfileManagerCtrl';
import ReceptionCtrl from '../controllers/ReceptionCtrl';
import SearchCtrl from '../controllers/SearchCtrl';
import TagsCtrl from '../controllers/TagsCtrl';
import UserDropdownCtrl from '../controllers/UserDropdownCtrl';
import UserSettingsCtrl from '../controllers/UserSettingsCtrl';
import UtilCtrl from '../controllers/UtilCtrl';
import VersionCtrl from '../controllers/VersionCtrl';

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
    'permission.ui',
    'permission',
    'relativeDate',
    'smart-table',
    'treeControl',
    'treeGrid',
    'ui.bootstrap.contextMenu',
    'ui.bootstrap.datetimepicker',
    'ui.bootstrap',
    'ui.dateTimeInput',
    'ui.router',
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
    BaseCtrl,
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
    CreateDipCtrl,
  ])
  .controller('HeadCtrl', ['$scope', '$rootScope', '$translate', '$state', HeadCtrl])
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
    MediaInformationCtrl,
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
    SearchCtrl,
  ])
  .controller('TagsCtrl', ['$scope', 'vm', '$http', 'appConfig', TagsCtrl])
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
    UtilCtrl,
  ])
  .controller('VersionCtrl', ['$scope', '$window', '$anchorScroll', '$location', '$translate', 'Sysinfo', VersionCtrl])
  .factory('Organization', ['$rootScope', '$http', '$state', 'appConfig', 'myService', organization]).name;
