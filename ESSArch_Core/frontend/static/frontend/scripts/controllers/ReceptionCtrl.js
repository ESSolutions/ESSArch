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

export default class ReceptionCtrl {
  constructor(
    IPReception,
    IP,
    StoragePolicy,
    $log,
    $uibModal,
    $scope,
    appConfig,
    $state,
    $rootScope,
    listViewService,
    Resource,
    $translate,
    $controller,
    ContextMenuBase,
    SelectedIPUpdater,
    $filter,
    $transitions
  ) {
    const vm = this;
    const ipSortString = [];
    const watchers = [];
    $controller('BaseCtrl', {$scope: $scope, vm: vm, ipSortString: ipSortString, params: {}});
    $scope.includedIps = [];
    $scope.profileEditor = false;
    //Request form data
    $scope.initRequestData = function () {
      vm.request = {
        type: 'receive',
        purpose: '',
        storagePolicy: {
          value: null,
          options: [],
        },
        submissionAgreement: {
          value: null,
          options: [],
          disabled: false,
        },
        informationClass: null,
        allowUnknownFiles: false,
      };
    };
    $scope.initRequestData();
    $transitions.onSuccess({}, function ($transition) {
      watchers.forEach(function (watcher) {
        watcher();
      });
    });

    $scope.menuOptions = function (rowType, row) {
      const methods = [];
      if (row.state === 'Prepared') {
        if ($scope.checkPermission('ip.change_organization')) {
          methods.push(
            ContextMenuBase.changeOrganization(function () {
              $scope.ip = row;
              $rootScope.ip = row;
              vm.changeOrganizationModal(rowType, $scope.ip);
            })
          );
        }
      }
      return methods;
    };

    //Get data for status view

    /*******************************************/
    /*Piping and Pagination for List-view table*/
    /*******************************************/

    $scope.selectedProfileRow = {profile_type: '', class: ''};
    vm.displayedIps = [];
    //Get data according to ip table settings and populates ip table
    vm.callServer = function callServer(tableState) {
      $scope.ipLoading = true;
      if (vm.displayedIps.length == 0) {
        $scope.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        $scope.tableState = tableState;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.itemsPerPage);
        Resource.getReceptionPage(paginationParams, tableState, sorting, search, ipSortString, vm.columnFilters)
          .then(function (result) {
            vm.displayedIps = result.data;
            tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
            $scope.ipLoading = false;
            $scope.initLoad = false;
            SelectedIPUpdater.update(vm.displayedIps, $scope.ips, $scope.ip);
          })
          .catch(function (response) {
            if (response.status == 404) {
              const filters = angular.extend(
                {
                  state: ipSortString,
                },
                vm.columnFilters
              );

              listViewService.checkPages('reception', paginationParams.number, filters).then(function (result) {
                tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
                tableState.pagination.start = result.numberOfPages * paginationParams.number - paginationParams.number;
                vm.callServer(tableState);
              });
            }
          });
      }
    };

    //Click function for Ip table
    vm.selectSingleRow = function (row, options) {
      if ($scope.ip !== null && $scope.ip.id == row.id) {
        $scope.ip = null;
        $rootScope.ip = null;
        if (angular.isUndefined(options) || !options.noStateChange) {
          $state.go($state.current.name, {id: null});
        }
        $scope.profileEditor = false;
      } else {
        vm.deselectAll();
        if (row.url) {
          row.url = appConfig.djangoUrl + 'ip-reception/' + row.id + '/';
        }
        $scope.ip = row;
        $rootScope.ip = row;
        if (angular.isUndefined(options) || !options.noStateChange) {
          $state.go($state.current.name, {id: row.id});
        }
        $scope.getFileList(row);
      }
    };

    vm.formatSdLabel = (key) => {
      return key
        .toLowerCase()
        .split('_')
        .map((x) => {
          return x.charAt(0).toUpperCase() + x.slice(1);
        })
        .join(' ');
    };

    vm.parseAltrecordIds = (obj) => {
      let parsed = {};
      angular.forEach(obj, (val, key) => {
        if (key.slice(0, 8) !== 'PROFILE_' && val[0] && val[0].slice(0, 8) !== 'ESSARCH_') {
          parsed[key] = val;
        }
      });
      return parsed;
    };

    $scope.getFileList = function (ip) {
      const array = [];
      const tempElement = {
        filename: ip.object_path,
        created: ip.create_date,
        size: ip.object_size,
      };
      array.push(tempElement);
      $scope.fileListCollection = array;
    };

    //Reload current view
    $scope.reloadPage = function () {
      $state.reload();
    };
    $scope.yes = $translate.instant('YES');
    $scope.no = $translate.instant('NO');

    $scope.getStoragePolicies = function () {
      return StoragePolicy.query().$promise.then(function (data) {
        return data;
      });
    };

    // Remove ip
    $scope.removeIp = function (ipObject) {
      IP.delete({
        id: ipObject.id,
      }).$promise.then(function () {
        $scope.edit = false;
        $scope.select = false;
        $scope.eventlog = false;
        $scope.eventShow = false;
        $scope.statusShow = false;
        $scope.filebrowser = false;
        $scope.requestForm = false;
        if (vm.displayedIps.length == 0) {
          $state.reload();
        }
        vm.uncheckIp(ipObject);
        $scope.getListViewData();
      });
    };

    //Create and show modal for receive ip
    $scope.receiveModal = function (ips) {
      if (ips.length === 0 && $scope.ip) {
        ips = [$scope.ip];
      }
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/receive_modal.html',
        controller: 'ReceiveModalInstanceCtrl',
        size: 'lg',
        controllerAs: '$ctrl',
        resolve: {
          data: function () {
            return {
              ips: angular.copy(ips),
            };
          },
        },
      });
      modalInstance.result.then(
        function (data) {
          $scope.ip = null;
          $rootScope.ip = null;
          $scope.ips = [];
          $scope.initRequestData();
          $timeout(function () {
            $scope.getListViewData();
          });
        },
        function () {
          $scope.getListViewData();
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    $scope.informationClassAlert = null;
    $scope.alerts = {
      matchError: {type: 'danger', msg: $translate.instant('MATCH_ERROR')},
    };
    $scope.closeAlert = function () {
      $scope.informationClassAlert = null;
    };

    vm.uncheckAll = function () {
      $scope.includedIps = [];
      vm.displayedIps.forEach(function (row) {
        row.checked = false;
      });
    };

    $scope.clickSubmit = function () {
      if (vm.requestForm.$valid) {
        $scope.receive($scope.ips);
      }
    };
  }
}
