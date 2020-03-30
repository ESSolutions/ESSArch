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

import {nestedEmptyPermissions, nestedPermissions, resolve} from '../index';

export default class UtilCtrl {
  /*@ngInject*/
  constructor(
    Notifications,
    $scope,
    $state,
    $timeout,
    myService,
    permissionConfig,
    $anchorScroll,
    $transitions,
    $window,
    $translate
  ) {
    $scope.angular = angular;
    $scope.$state = $state;
    $scope.reloadPage = function () {
      $state.reload();
    };
    $scope.infoPage = function () {
      $state.go('home.info');
    };
    $scope.checkPermissions = function (page) {
      // Check if there is a sub state that does not require permissions
      if (nestedEmptyPermissions(resolve(page, permissionConfig))) {
        return true;
      }
      const permissions = nestedPermissions(resolve(page, permissionConfig));
      return myService.checkPermissions(permissions);
    };
    $scope.showAlert = function () {
      Notifications.toggle();
    };

    $scope.navigateToState = function (state) {
      $state.go(state);
    };

    $scope.gotoDocs = function () {
      $window.open('/docs/' + $translate.use() + '/user_guide/index.html', '_blank');
    };

    const enter = 13;
    const space = 32;

    let stateChangeListeners = [];
    function resetStateListeners() {
      stateChangeListeners.forEach(function (listener) {
        listener();
      });
      stateChangeListeners = [];
    }
    /**
     * Handle keydown events navigation
     * @param {Event} e
     */
    $scope.navKeydownListener = function (e, state) {
      switch (e.keyCode) {
        case space:
        case enter:
          e.preventDefault();
          stateChangeListeners.push(
            $transitions.onSuccess({}, function ($transition) {
              $transition.abort();
              if (
                state == 'home.ingest' ||
                state == 'home.access' ||
                state == 'home.administration' ||
                state == 'home.archiveMaintenance'
              ) {
                $scope.focusSubmenu();
              } else if (state == 'home.administration.profileManager') {
                $scope.focusProfileManagerSubmenu();
              } else if (state.match(/home\.administration\.profileManager/)) {
                $scope.focusProfileManagerRouterView();
              } else {
                $scope.focusRouterView();
              }
              resetStateListeners();
            })
          );
          $state.go(state);
          break;
      }
    };
    $scope.focusRouterView = function () {
      $timeout(function () {
        const elm = document.getElementsByClassName('dynamic-part')[0];
        elm.focus();
        $anchorScroll();
      });
    };
    $scope.focusSubmenu = function () {
      $timeout(function () {
        const elm = document.getElementsByClassName('sub-menu')[0];
        angular.element(elm)[0].children[0].focus();
        $anchorScroll();
      });
    };
    $scope.focusProfileManagerSubmenu = function () {
      $timeout(function () {
        const elm = document.getElementsByClassName('profile-manager-sub-menu')[0];
        angular.element(elm)[0].children[0].focus();
        $anchorScroll();
      });
    };
    $scope.focusProfileManagerRouterView = function () {
      $timeout(function () {
        const elm = document.getElementsByClassName('profile-manager-route')[0];
        angular.element(elm)[0].focus();
        $anchorScroll();
      });
    };
  }
}
