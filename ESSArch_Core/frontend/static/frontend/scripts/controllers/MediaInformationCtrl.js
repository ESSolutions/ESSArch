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

export default class MediaInformationCtrl {
  constructor(
    $scope,
    $rootScope,
    $controller,
    appConfig,
    Resource,
    $interval,
    SelectedIPUpdater,
    listViewService,
    $transitions
  ) {
    const vm = this;
    const watchers = [];
    $controller('BaseCtrl', {$scope: $scope, vm: vm, ipSortString: '', params: {}});
    $scope.colspan = 6;
    $scope.storageMedium = null;
    $rootScope.storageMedium = null;
    vm.storageObjects = [];
    vm.objectsPerPage = 10;
    let mediumInterval;
    let objectInterval;
    $interval.cancel(mediumInterval);
    mediumInterval = $interval(function() {
      vm.getMediumData();
    }, appConfig.storageMediumInterval);
    watchers.push(
      $scope.$watch(
        function() {
          return $scope.select;
        },
        function(newValue, oldValue) {
          if (newValue) {
            $interval.cancel(objectInterval);
            objectInterval = $interval(function() {
              vm.getObjectData();
            }, appConfig.storageObjectInterval);
          } else {
            $interval.cancel(objectInterval);
          }
        }
      )
    );
    $transitions.onSuccess({}, function($transition) {
      watchers.forEach(function(watcher) {
        watcher();
      });
    });
    //Cancel update intervals on state change
    $transitions.onSuccess({}, function($transition) {
      $interval.cancel(mediumInterval);
      $interval.cancel(objectInterval);
    });

    $scope.storageMediumTableClick = function(row) {
      if ($scope.select && $scope.storageMedium.id == row.id) {
        $scope.select = false;
        $scope.eventlog = false;
        $scope.edit = false;
        $scope.eventShow = false;
        $scope.storageMedium = null;
        $rootScope.storageMedium = null;
      } else {
        $scope.storageMedium = row;
        $rootScope.storageMedium = row;
        vm.getObjectData();
        $scope.select = true;
        $scope.eventlog = true;
        $scope.edit = true;
      }
      $scope.statusShow = false;
    };

    $scope.updateStorageMediums = function() {
      vm.callServer($scope.mediumTableState);
    };
    /*******************************************/
    /*Piping and Pagination for List-view table*/
    /*******************************************/
    vm.displayedMediums = [];
    //Get data according to ip table settings and populates ip table
    vm.callServer = function callServer(tableState) {
      $scope.ipLoading = true;
      if (vm.displayedMediums.length == 0) {
        $scope.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        vm.mediumTableState = tableState;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.itemsPerPage);
        Resource.getStorageMediums(paginationParams, tableState, sorting, search)
          .then(function(result) {
            vm.displayedMediums = result.data;
            tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
            $scope.ipLoading = false;
            $scope.initLoad = false;
            SelectedIPUpdater.update(vm.displayedMediums, [], $scope.storageMedium);
          })
          .catch(function(response) {
            if (response.status == 404) {
              const filters = {
                search: search,
              };

              listViewService.checkPages('storage_medium', paginationParams.number, filters).then(function(result) {
                tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
                tableState.pagination.start = result.numberOfPages * paginationParams.number - paginationParams.number;
                vm.callServer(tableState);
              });
            } else {
              $scope.ipLoading = false;
            }
          });
      }
    };
    vm.objectPipe = function objectPipe(tableState) {
      $scope.objectLoading = true;
      if (vm.storageObjects.length == 0) {
        $scope.initObjLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        vm.objectTableState = tableState;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.objectsPerPage);
        Resource.getStorageObjectsForMedium(
          $scope.storageMedium.id,
          paginationParams,
          tableState,
          $scope.storageMedium,
          sorting,
          search
        )
          .then(function(result) {
            vm.storageObjects = result.data;
            tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
            $scope.objectLoading = false;
            $scope.initObjLoad = false;
          })
          .catch(function(response) {
            if (response.status == 404) {
              const filters = {
                search: search,
              };

              listViewService.checkPages('storage_object', paginationParams.number, filters).then(function(result) {
                tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
                tableState.pagination.start = result.numberOfPages * paginationParams.number - paginationParams.number;
                vm.objectPipe(tableState);
              });
            }
          });
      }
    };
    vm.getMediumData = function() {
      vm.callServer(vm.mediumTableState);
    };
    vm.getObjectData = function() {
      vm.objectPipe(vm.objectTableState);
    };
    $scope.searchDisabled = function() {
      if ($scope.filterModels.length > 0) {
        if ($scope.filterModels[0].column != null) {
          delete $scope.tableState.search.predicateObject;
          return true;
        }
      } else {
        return false;
      }
    };
    $scope.clearSearch = function() {
      delete $scope.tableState.search.predicateObject;
      $('#search-input')[0].value = '';
      $scope.getListViewData();
    };
  }
}
