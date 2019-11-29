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

export default class PrepareSipCtrl {
  constructor(
    Profile,
    $log,
    $uibModal,
    $scope,
    $rootScope,
    $http,
    appConfig,
    listViewService,
    $anchorScroll,
    $controller,
    $timeout,
    $state,
    ContentTabs,
    $translate
  ) {
    const vm = this;
    const ipSortString = ['Created', 'Submitting', 'Submitted'];
    const params = {
      package_type: 0,
    };
    $controller('BaseCtrl', {$scope: $scope, vm: vm, ipSortString: ipSortString, params});
    vm.fileListLoading = false;

    $scope.menuOptions = function(rowType, row) {
      const methods = [];
      methods.push({
        text: $translate.instant('INFORMATION_PACKAGE_INFORMATION'),
        click: function($itemScope, $event, modelValue, text, $li) {
          vm.ipInformationModal(row);
        },
      });
      return methods;
    };

    //Click function for ip table
    vm.selectSingleRow = function(row, options) {
      $scope.ips = [];
      if ($scope.ip !== null && $scope.ip.id == row.id) {
        $scope.ip = null;
        $rootScope.ip = null;
        if (angular.isUndefined(options) || !options.noStateChange) {
          $state.go($state.current.name, {id: null});
        }
      } else {
        $scope.ip = null;
        $rootScope.ip = null;
        vm.activeTab = null;
        const ip = row;
        $scope.ip = row;
        $rootScope.ip = row;
        if (angular.isUndefined(options) || !options.noStateChange) {
          $state.go($state.current.name, {id: ip.id});
        }
        if (vm.specificTabs.includes('submit_sip') || ContentTabs.visible([ip], $state.current.name)) {
          vm.fileListLoading = true;
          listViewService.getFileList(ip).then(function(result) {
            $scope.fileListCollection = result;
            vm.fileListLoading = false;
            return result;
          });
        }
      }
    };

    // Populate file list view
    vm.options = {
      formState: {},
    };
    //Get list of files in ip
    $scope.getFileList = function(ip) {
      listViewService.getFileList(ip).then(function(result) {
        $scope.fileListCollection = result;
      });
    };

    vm.submitSipModal = function(ip) {
      const ips = $scope.ips.length > 0 ? $scope.ips : null;
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/submit_sip_modal.html',
        scope: $scope,
        controller: 'DataModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            ip: ip,
            ips: ips,
            vm: vm,
          },
        },
      });
      modalInstance.result
        .then(function(data) {
          $scope.ips = [];
          $scope.ip = null;
          $rootScope.ip = null;
          $scope.getListViewData();
          vm.updateListViewConditional();
          $anchorScroll();
        })
        .catch(function() {
          $log.info('modal-component dismissed at: ' + new Date());
        });
    };
  }
}
