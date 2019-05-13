import AccessCtrl from '../controllers/AccessCtrl';
import AccessIpCtrl from '../controllers/AccessIpCtrl';
import AdministrationCtrl from '../controllers/AdministrationCtrl';
import AppCtrl from '../controllers/AppCtrl';
import BaseCtrl from '../controllers/BaseCtrl';
import HeadCtrl from '../controllers/HeadCtrl';
import IngestCtrl from '../controllers/IngestCtrl';
import IpApprovalCtrl from '../controllers/IpApprovalCtrl';
import LanguageCtrl from '../controllers/LanguageCtrl';
import MyPageCtrl from '../controllers/MyPageCtrl';
import {organization, OrganizationCtrl} from '../controllers/OrganizationCtrl';
import ProfileManagerCtrl from '../controllers/ProfileManagerCtrl';
import ReceptionCtrl from '../controllers/ReceptionCtrl';
import SearchCtrl from '../controllers/SearchCtrl';
import TagsCtrl from '../controllers/TagsCtrl';
import UserDropdownCtrl from '../controllers/UserDropdownCtrl';
import UtilCtrl from '../controllers/UtilCtrl';

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
  .controller('AccessIpCtrl', AccessIpCtrl)
  .controller('AdministrationCtrl', AdministrationCtrl)
  .controller('AppCtrl', AppCtrl)
  .controller('BaseCtrl', BaseCtrl)
  .controller('HeadCtrl', HeadCtrl)
  .controller('IngestCtrl', IngestCtrl)
  .controller('IpApprovalCtrl', IpApprovalCtrl)
  .controller('LanguageCtrl', LanguageCtrl)
  .controller('MyPageCtrl', MyPageCtrl)
  .controller('OrganizationCtrl', OrganizationCtrl)
  .controller('ProfileManagerCtrl', ProfileManagerCtrl)
  .controller('ReceptionCtrl', ReceptionCtrl)
  .controller('SearchCtrl', SearchCtrl)
  .controller('TagsCtrl', TagsCtrl)
  .controller('UserDropdownCtrl', UserDropdownCtrl)
  .controller('UtilCtrl', UtilCtrl)
  .factory('Organization', organization).name;
