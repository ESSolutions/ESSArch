import '@flowjs/ng-flow';
import 'angular-animate';
import 'angular-bootstrap-contextmenu';
import 'angular-bootstrap-grid-tree';
import 'angular-clipboard';
import 'angular-cookies';
import 'angular-cron-jobs';
import 'angular-date-time-input';
import 'angular-filesize-filter';
import 'angular-formly-templates-bootstrap';
import 'angular-formly';
import 'angular-link-header-parser';
import 'angular-marked';
import 'angular-messages';
import 'angular-permission';
import 'angular-relative-date';
import 'angular-resizable';
import 'angular-resource';
import 'angular-sanitize';
import 'angular-smart-table';
import 'angular-translate-loader-static-files';
import 'angular-translate-storage-cookie';
import 'angular-translate';
import 'angular-tree-control';
import 'angular-ui-bootstrap';
import 'angular-ui-router';
import 'angular-websocket';
import 'angularjs-bootstrap-datetimepicker';
//import ngJsTree from 'ng-js-tree';
import 'ui-select';

import AppCtrl from '../controllers/AppCtrl';
import BaseCtrl from '../controllers/BaseCtrl';
import HeadCtrl from '../controllers/HeadCtrl';
import IngestCtrl from '../controllers/IngestCtrl';
import LanguageCtrl from '../controllers/LanguageCtrl';
import MyPageCtrl from '../controllers/MyPageCtrl';
import ReceptionCtrl from '../controllers/ReceptionCtrl';
import {organization, OrganizationCtrl} from '../controllers/OrganizationCtrl';
import UtilCtrl from '../controllers/UtilCtrl';
import UserDropdownCtrl from '../controllers/UserDropdownCtrl';

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
  .controller('AppCtrl', AppCtrl)
  .controller('BaseCtrl', BaseCtrl)
  .controller('HeadCtrl', HeadCtrl)
  .controller('IngestCtrl', IngestCtrl)
  .controller('OrganizationCtrl', OrganizationCtrl)
  .controller('LanguageCtrl', LanguageCtrl)
  .controller('MyPageCtrl', MyPageCtrl)
  .controller('ReceptionCtrl', ReceptionCtrl)
  .controller('UserDropdownCtrl', UserDropdownCtrl)
  .controller('UtilCtrl', UtilCtrl)
  .factory('Organization', organization).name;
