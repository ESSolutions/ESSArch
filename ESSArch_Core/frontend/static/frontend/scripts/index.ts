/*
ESSArch is an open source archiving and digital preservation system

ESSArch
Copyright (C) 2005-2019 ES Solutions AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

Contact information:
Web - http://www.essolutions.se
Email - essarch@essolutions.se
*/

import * as angular from 'angular';
import uiRouter, {
  UrlService,
  StateService,
  StateProvider,
  TransitionService,
  UrlParts,
  UIRouter,
} from '@uirouter/angularjs';
import {permission, uiPermission} from 'angular-permission';

import '@flowjs/ng-flow';
import 'angular-animate';
import 'angularjs-bootstrap-datetimepicker';
import 'angular-bootstrap-contextmenu';
import 'angular-bootstrap-grid-tree';
import 'angular-clipboard';
import 'angular-cookies';
import 'angular-cron-jobs';
import 'angular-date-time-input';
import 'angular-filesize-filter';
import 'angular-formly';
import 'angular-formly-templates-bootstrap';
import 'angular-link-header-parser';
import 'angular-marked';
import 'angular-messages';
import 'angular-mocks';
import 'angular-pretty-xml';
import 'angular-relative-date';
import 'angular-resource';
import 'angular-resizable';
import 'angular-sanitize';
import 'angular-smart-table';
import 'angular-translate';
import 'angular-translate-loader-static-files';
import 'angular-translate-storage-cookie';
import 'angular-tree-control';
import 'angular-ui-bootstrap';
import 'angular-websocket';
import 'messenger-hubspot';
import 'moment';
import 'ui-select';
import {UAParser} from 'ua-parser-js';

import authentication from './authentication';
import notifications from './notifications';
import utils from './utils';
import essarchLanguageModule from './modules/essarch.language.module';
import essarchControllersModule from './modules/essarch.controllers.module';
import essarchServicesModule from './modules/essarch.services.module';
import essarchConfigsModule from './modules/essarch.configs.module';
import essarchComponentsModule from './modules/essarch.components.module';
import essarchDirectivesModule from './modules/essarch.directives.module';

import '../styles/styles.scss';
import {IFormlyConfig, IValidationMessages} from 'AngularFormly';

export const resolve = (path: string, obj: object) => {
  return path.split('.').reduce(function(prev, curr) {
    return prev ? prev[curr] : undefined;
  }, obj || self);
};

export const nestedPermissions = (page: string[] | object): string[] => {
  // If page is an array it means that page is the field _permissions
  if (Array.isArray(page)) {
    return page;
  } else if (typeof page == 'object') {
    let temp = [];
    for (const entry in page) {
      // Recursively build permission list
      temp = temp.concat(nestedPermissions(page[entry]));
    }
    return temp;
  }
};

/**
 * Check if state has a sub state that requires no permissions
 * @param {*} page
 */
export const nestedEmptyPermissions = (page: object[] | object): boolean => {
  if (Array.isArray(page)) {
    return page.length == 0;
  } else if (typeof page == 'object') {
    for (const entry in page) {
      if (nestedEmptyPermissions(page[entry])) {
        return true;
      }
    }
    return false;
  }
};

const resolveAuthenticated = [
  'djangoAuth',
  function(djangoAuth) {
    return djangoAuth.authenticationStatus();
  },
];

angular
  .module('essarch', [
    essarchLanguageModule,
    essarchControllersModule,
    essarchServicesModule,
    essarchConfigsModule,
    essarchComponentsModule,
    essarchDirectivesModule,
    'formly',
    'formlyBootstrap',
    uiRouter,
    permission,
    uiPermission,
    'ngCookies',
    'pascalprecht.translate',
    'ngSanitize',
    'ui.bootstrap.datetimepicker',
    'essarch.appConfig',
    'permission.config',
    authentication,
    notifications,
    utils,
  ])
  .config([
    '$urlMatcherFactoryProvider',
    '$stateProvider',
    '$urlServiceProvider',
    'permissionConfig',
    function(
      $urlMatcherFactoryProvider,
      $stateProvider: StateProvider,
      $urlServiceProvider: UrlService,
      permissionConfig
    ) {
      $urlMatcherFactoryProvider.strictMode(false);

      $stateProvider
        .state('home', {
          url: '/',
          templateUrl: '/static/frontend/views/home.html',
        })
        .state('login', {
          url: '/login',
          params: {
            requestedPage: '/login',
          },
          templateUrl: '/static/frontend/views/login.html',
          controller: 'LoginCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
        })
        .state('home.userSettings', {
          url: 'user-settings',
          templateUrl: '/static/frontend/views/user_settings.html',
          controller: 'UserSettingsCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
        })
        .state('home.info', {
          url: 'info',
          templateUrl: '/static/frontend/views/my_page.html',
          controller: 'MyPageCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
        })
        .state('home.producer', {
          url: 'producer',
          templateUrl: '/static/frontend/views/producer.html',
          resolve: {
            authenticated: resolveAuthenticated,
          },
        })
        .state('home.producer.prepareIp', {
          url: '/prepare-IP/{id}',
          templateUrl: '/static/frontend/views/create_sip_prepare_ip.html',
          controller: 'PrepareIpCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          params: {
            id: {dynamic: true, value: null},
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.producer.prepareIp', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.producer.collectContent', {
          url: '/collect-content/{id}',
          templateUrl: '/static/frontend/views/create_sip_collect_content.html',
          controller: 'CollectContentCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          params: {
            id: {dynamic: true, value: null},
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.producer.collectContent', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.producer.dataSelection', {
          url: '/data-selection',
          templateUrl: '/static/frontend/views/create_sip_data_selection.html',
          controller: 'PrepareIpCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
        })
        .state('home.producer.dataExtraction', {
          url: '/data-extraction',
          templateUrl: '/static/frontend/views/create_sip_data_extraction.html',
          controller: 'PrepareIpCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
        })
        .state('home.producer.manageData', {
          url: '/manage-data',
          templateUrl: '/static/frontend/views/create_sip_manage_data.html',
          controller: 'PrepareIpCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
        })
        .state('home.producer.createSip', {
          url: '/create-SIP/{id}',
          templateUrl: '/static/frontend/views/create_sip_ip_approval.html',
          controller: 'CreateSipCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          params: {
            id: {dynamic: true, value: null},
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.producer.createSip', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.producer.submitSip', {
          url: '/submit-SIP/{id}',
          templateUrl: '/static/frontend/views/submit_sip_prepare_sip.html',
          controller: 'PrepareSipCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          params: {
            id: {dynamic: true, value: null},
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.submitSip.prepareSip', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.ingest', {
          url: 'ingest',
          templateUrl: '/static/frontend/views/ingest.html',
          controller: 'IngestCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
        })
        .state('home.ingest.reception', {
          url: '/reception/{id}',
          templateUrl: '/static/frontend/views/reception.html',
          controller: 'ReceptionCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          params: {
            id: {dynamic: true, value: null},
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.ingest.reception', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.ingest.ipApproval', {
          url: '/approval/{id}',
          templateUrl: '/static/frontend/views/ip_approval.html',
          controller: 'IpApprovalCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          params: {
            id: {dynamic: true, value: null},
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.ingest.ipApproval', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.access', {
          url: 'access',
          templateUrl: '/static/frontend/views/access.html',
          controller: 'AccessCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
        })
        .state('home.access.accessIp', {
          url: '/access-IP/{id}',
          templateUrl: '/static/frontend/views/access_ip.html',
          controller: 'AccessIpCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          params: {
            id: {dynamic: true, value: null},
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.access.accessIp', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.access.orders', {
          url: '/orders/{id}',
          templateUrl: '/static/frontend/views/orders.html',
          controller: 'OrdersCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          params: {
            id: {dynamic: true, value: null},
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.orders', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.access.createDip', {
          url: '/create-DIP/{id}',
          templateUrl: '/static/frontend/views/access_create_dip.html',
          controller: 'CreateDipCtrl as vm',
          params: {
            id: {dynamic: true, value: null},
          },
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.access.createDip', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.archivalDescriptions', {
          url: 'archival-descriptions',
          templateUrl: '/static/frontend/views/archival_descriptions.html',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.archivalDescriptions', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.archivalDescriptions.search', {
          url: '/search?{query:json}',
          templateUrl: '/static/frontend/views/search.html',
          controller: 'SearchCtrl as vm',
          params: {
            query: {dynamic: true},
          },
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.archivalDescriptions.search', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.archivalDescriptions.search.information_package', {
          url: '/information_package/:id',
          templateUrl: '/static/frontend/views/search_ip_detail.html',
          controller: 'SearchIpCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.archivalDescriptions.search', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.archivalDescriptions.search.component', {
          url: '/component/:id',
          templateUrl: '/static/frontend/views/search_detail.html',
          controller: 'SearchDetailCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.archivalDescriptions.search', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.archivalDescriptions.search.structure_unit', {
          url: '/structure-unit/:id?{archive}',
          templateUrl: '/static/frontend/views/search_structure_unit_detail.html',
          controller: 'SearchDetailCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.archivalDescriptions.search', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.archivalDescriptions.search.directory', {
          url: '/directory/:id',
          templateUrl: '/static/frontend/views/search_detail.html',
          controller: 'SearchDetailCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.archivalDescriptions.search', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.archivalDescriptions.search.document', {
          url: '/document/:id',
          templateUrl: '/static/frontend/views/search_detail.html',
          controller: 'SearchDetailCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.archivalDescriptions.search', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.archivalDescriptions.search.archive', {
          url: '/archive/:id',
          templateUrl: '/static/frontend/views/search_detail.html',
          controller: 'SearchDetailCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.archivalDescriptions.search', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.archivalDescriptions.archiveCreators', {
          url: '/archive-creators/{id}',
          template: '<agents></agents>',
          params: {
            id: {
              dynamic: true,
              value: null,
            },
          },
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.archivalDescriptions.archiveCreators', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.archivalDescriptions.classificationStructures', {
          url: '/structures/{id}',
          template: '<classification-structure-editor></classification-structure-editor>',
          params: {
            id: {dynamic: true, value: null},
          },
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.archivalDescriptions.classificationStructures', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.archivalDescriptions.archiveManager', {
          url: '/archive-manager',
          template: '<archive-manager></archive-manager>',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.archivalDescriptions.archiveManager', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.archivalDescriptions.archiveManager.detail', {
          url: '/:id',
          templateUrl: '/static/frontend/views/search_archive_detail.html',
          controller: 'SearchDetailCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.archivalDescriptions.archiveManager', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.archivalDescriptions.location', {
          url: '/location/{id}',
          template: '<location></location>',
          params: {
            id: {dynamic: true, value: null},
          },
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.archivalDescriptions.location', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.archivalDescriptions.deliveries', {
          url: '/deliveries/{delivery}',
          template: '<delivery-page></delivery-page>',
          params: {
            transfer: {dynamic: true, value: null},
            delivery: {dynamic: true, value: null},
          },
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.archivalDescriptions.deliveries', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.archivalDescriptions.deliveries.transfers', {
          url: '/transfers/{transfer}',
          templateUrl: 'static/frontend/views/transfers.html',
          controller: 'TransferCtrl',
          controllerAs: 'vm',
          params: {
            transfer: {dynamic: true, value: null},
            delivery: {dynamic: true, value: null},
          },
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.archivalDescriptions.deliveries.transfers', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.workarea', {
          url: 'workspace/{id}',
          templateUrl: '/static/frontend/views/combined_workarea.html',
          controller: 'CombinedWorkareaCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          params: {
            id: {dynamic: true, value: null},
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.workarea', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.management', {
          url: 'management',
          templateUrl: '/static/frontend/views/management.html',
          controller: 'ManagementCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.management', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.archiveMaintenance', {
          url: 'archive-maintenance',
          templateUrl: '/static/frontend/views/archive_maintenance.html',
          resolve: {
            authenticated: resolveAuthenticated,
          },
        })
        .state('home.archiveMaintenance.start', {
          url: '/start',
          templateUrl: '/static/frontend/views/archive_maintenance_start.html',
          controller: 'AppraisalCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.archiveMaintenance.start', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.archiveMaintenance.appraisal', {
          url: '/appraisal',
          templateUrl: '/static/frontend/views/appraisal.html',
          controller: 'AppraisalCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.archiveMaintenance.appraisal', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.archiveMaintenance.conversion', {
          url: '/conversion',
          templateUrl: '/static/frontend/views/conversion.html',
          controller: 'ConversionCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.archiveMaintenance.appraisal', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.administration', {
          url: 'administration',
          templateUrl: '/static/frontend/views/administration.html',
          controller: 'AdministrationCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
        })
        .state('home.administration.mediaInformation', {
          url: '/media-information',
          templateUrl: '/static/frontend/views/administration_media_information.html',
          controller: 'MediaInformationCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.administration.mediaInformation', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.administration.robotInformation', {
          url: '/robot-information',
          templateUrl: '/static/frontend/views/administration_robot_information.html',
          controller: 'RobotInformationCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.administration.robotInformation', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.administration.queues', {
          url: '/queues',
          templateUrl: 'static/frontend/views/administration_queues.html',
          controller: 'QueuesCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.administration.queues', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.administration.storageMigration', {
          url: '/storage-migration',
          templateUrl: 'static/frontend/views/administration_storage_migration.html',
          controller: 'StorageMigrationCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.administration.storageMigration', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.administration.storageMaintenance', {
          url: '/storage-maintenance',
          templateUrl: 'static/frontend/views/administration_storage_maintenance.html',
          controller: 'StorageMaintenanceCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.administration.storageMaintenance', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.administration.profileManager', {
          url: '/profile-manager',
          templateUrl: 'static/frontend/views/profile_manager.html',
          controller: 'ProfileManagerCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.administration.profileManager', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.administration.profileManager.saEditor', {
          url: '/sa-editor',
          template: '<sa-editor></sa-editor>',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.administration.profileManager.saEditor', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.administration.profileManager.import', {
          url: '/import',
          template: '<import></import>',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.administration.profileManager.import', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.administration.profileManager.export', {
          url: '/export',
          template: '<export></export>',
          resolve: {
            authenticated: resolveAuthenticated,
          },
          data: {
            permissions: {
              only: nestedPermissions(resolve('home.administration.profileManager.export', permissionConfig)),
              redirectTo: 'home.restricted',
            },
          },
        })
        .state('home.system', {
          url: 'system',
          templateUrl: '/static/frontend/views/sysinfo.html',
          controller: 'VersionCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
        })
        .state('home.support', {
          url: 'support',
          templateUrl: '/static/frontend/views/support.html',
          controller: 'VersionCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
        })
        .state('home.restricted', {
          url: 'restricted',
          templateUrl: '/static/frontend/views/restricted.html',
          controller: 'RestrictedCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
        })
        .state('authRequired', {
          url: '/auth-required',
          templateUrl: '/static/frontend/views/auth_required.html',
          controller: 'AuthRequiredCtrl as vm',
          resolve: {
            authenticated: resolveAuthenticated,
          },
        });
      $urlServiceProvider.rules.otherwise((_matchValue?: any, _url?: UrlParts, router?: UIRouter) => {
        router.stateService.go('home.info');
      });

      $urlServiceProvider.deferIntercept();
    },
  ])
  .config([
    '$animateProvider',
    function($animateProvider) {
      // Only animate elements with the 'angular-animate' class
      $animateProvider.classNameFilter(/angular-animate|ui-select-/);
    },
  ])
  .config([
    'markedProvider',
    function(markedProvider) {
      function isURL(str) {
        const urlRegex =
          '^(?!mailto:)(?:(?:http|https|ftp)://)(?:\\S+(?::\\S*)?@)?(?:(?:(?:[1-9]\\d?|1\\d\\d|2[01]\\d|22[0-3])(?:\\.(?:1?\\d{1,2}|2[0-4]\\d|25[0-5])){2}(?:\\.(?:[0-9]\\d?|1\\d\\d|2[0-4]\\d|25[0-4]))|(?:(?:[a-z\\u00a1-\\uffff0-9]+-?)*[a-z\\u00a1-\\uffff0-9]+)(?:\\.(?:[a-z\\u00a1-\\uffff0-9]+-?)*[a-z\\u00a1-\\uffff0-9]+)*(?:\\.(?:[a-z\\u00a1-\\uffff]{2,})))|localhost)(?::\\d{2,5})?(?:(/|\\?|#)[^\\s]*)?$';
        const url = new RegExp(urlRegex, 'i');
        return str.length < 2083 && url.test(str);
      }
      markedProvider.setOptions({
        gfm: true,
        tables: true,
      });
      markedProvider.setRenderer({
        link: function(href, title, text) {
          if (!isURL(href)) {
            return '<a ng-click=\'scrollToLink("' + href + '")\'' + '>' + text + '</a>';
          } else {
            return (
              "<a href='" + href + "'" + (title ? " title='" + title + "'" : '') + " target='_blank'>" + text + '</a>'
            );
          }
        },
      });
    },
  ])
  .config([
    '$uibTooltipProvider',
    function($uibTooltipProvider) {
      const parser = new UAParser();
      const result = parser.getResult();
      const touch = result.device && (result.device.type === 'tablet' || result.device.type === 'mobile');
      if (touch) {
        $uibTooltipProvider.options({trigger: 'dontTrigger'});
      } else {
        $uibTooltipProvider.options({trigger: 'mouseenter', popupDelay: 1600});
      }
    },
  ])
  .config([
    '$resourceProvider',
    function($resourceProvider) {
      // Don't strip trailing slashes from calculated URLs
      $resourceProvider.defaults.stripTrailingSlashes = false;
    },
  ])
  .config([
    '$compileProvider',
    'appConfig',
    '$logProvider',
    function($compileProvider, appConfig, $logProvider) {
      $compileProvider.debugInfoEnabled(appConfig.debugInfo);
      $compileProvider.commentDirectivesEnabled(appConfig.commentDirectives);
      $compileProvider.cssClassDirectivesEnabled(appConfig.cssClassDirectives);
      $logProvider.debugEnabled(appConfig.logDebug);
    },
  ])
  .config([
    '$permissionProvider',
    function($permissionProvider) {
      $permissionProvider.suppressUndefinedPermissionWarning(true);
    },
  ])
  .config([
    'stConfig',
    function(stConfig) {
      stConfig.sort.delay = -1;
    },
  ])
  .config([
    '$compileProvider',
    function($compileProvider) {
      $compileProvider.aHrefSanitizationWhitelist(/^\s*(https?|ftp|mailto|tel|file|blob|data):/);
    },
  ])
  .directive('setTouched', function MainCtrl() {
    return {
      restrict: 'A', // only activate on element attribute
      require: '?ngModel', // get a hold of NgModelController
      link: function(scope, element, attrs, ngModel) {
        if (!ngModel) return; // do nothing if no ng-model
        element.on('blur', function() {
          const modelControllers = scope.$eval(attrs.setTouched);
          if (angular.isArray(modelControllers)) {
            angular.forEach(modelControllers, function(modelCntrl) {
              modelCntrl.$setTouched();
            });
          }
        });
      },
    };
  })
  .run([
    'djangoAuth',
    '$rootScope',
    '$state',
    '$location',
    '$http',
    'myService',
    'formlyConfig',
    'formlyValidationMessages',
    '$urlService',
    'permissionConfig',
    'appConfig',
    '$transitions',
    function(
      djangoAuth,
      $rootScope,
      $state: StateService,
      $location: ng.ILocationService,
      $http: ng.IHttpService,
      myService,
      formlyConfig: IFormlyConfig,
      formlyValidationMessages: IValidationMessages,
      $urlService: UrlService,
      permissionConfig,
      appConfig,
      $transitions: TransitionService
    ) {
      formlyConfig.extras.errorExistsAndShouldBeVisibleExpression = 'form.$submitted || fc.$touched || fc[0].$touched';
      formlyValidationMessages.addStringMessage('required', 'This field is required');
      $rootScope.app = 'ESSArch';
      $rootScope.flowObjects = {};
      djangoAuth
        .initialize('/api/auth', false)
        .then(function(response) {
          $rootScope.auth = response.data;
          myService.getPermissions(response.data.permissions);
          // kick-off router and start the application rendering
          $urlService.sync();
          // Also enable router to listen to url changes
          $urlService.listen();
          $rootScope.listViewColumns = myService.generateColumns(response.data.ip_list_columns).activeColumns;
          $http
            .get(appConfig.djangoUrl + 'site/')
            .then(function(response) {
              $rootScope.site = response.data;
            })
            .catch(function() {
              $rootScope.site = null;
            });
          $transitions.onStart({}, function($transition) {
            const to = $transition.to();
            if (to.name === 'login') {
              return;
            }
            if (djangoAuth.authenticated !== true) {
              console.log('Not authenticated, redirecting to login');
              $transition.abort();
              $state.go('login'); // go to login
            }
          });
        })
        .catch(function() {
          console.log('Got error response from auth api, redirecting to login with requested page:', $location.path());
          $state.go('login', {requestedPage: $location.path()});
        });

      $transitions.onStart({}, function($transition) {
        const to = $transition.to();
        const from = $transition.from();
        const params = $transition.params();

        if (to.redirectTo) {
          $transition.abort();
          $state.go(to.redirectTo.toString(), params, {location: 'replace'});
        }

        if (to.name == 'login' && djangoAuth.authenticated) {
          $transition.abort();
          if (from.name != '') {
            $state.transitionTo(from.name);
          } else {
            $state.transitionTo('home.info');
          }
        }

        if (
          to.name == 'home.producer' ||
          to.name == 'home.ingest' ||
          to.name == 'home.access' ||
          to.name == 'home.archivalDescriptions' ||
          to.name == 'home.administration' ||
          to.name == 'home.administration.profileManager' ||
          to.name == 'home.archiveMaintenance'
        ) {
          $transition.abort();
          const resolved = resolve(to.name, permissionConfig);
          for (const key in resolved) {
            if (key != '_permissions' && myService.checkPermissions(nestedPermissions(resolved[key]))) {
              $state.go(to.name + '.' + key);
              return;
            }
          }
          $state.go('home.restricted');
          return;
        }
      });
    },
  ]);
