/*
ESSArch is an open source archiving and digital preservation system

ESSArch Preservation Platform (EPP)
Copyright (C) 2005-2017 ES Solutions AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.

Contact information:
Web - http://www.essolutions.se
Email - essarch@essolutions.se
*/

angular
  .module('essarch.controllers')
  .controller('MediaInformationCtrl', function(
    $scope,
    $rootScope,
    $controller,
    $cookies,
    $http,
    appConfig,
    Resource,
    $interval,
    $anchorScroll,
    $timeout,
    SelectedIPUpdater
  ) {
    var vm = this;
    var watchers = [];
    $controller('BaseCtrl', {$scope: $scope, vm: vm, ipSortString: ''});
    $scope.colspan = 6;
    $scope.storageMedium = null;
    $rootScope.storageMedium = null;
    vm.storageObjects = [];
    vm.objectsPerPage = 10;
    var mediumInterval;
    var objectInterval;
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
    $scope.$on('$stateChangeStart', function() {
      watchers.forEach(function(watcher) {
        watcher();
      });
    });
    //Cancel update intervals on state change
    $scope.$on('$stateChangeStart', function() {
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
        var sorting = tableState.sort;
        var pagination = tableState.pagination;
        var start = pagination.start || 0; // This is NOT the page number, but the index of item in the list that you want to use to display the table.
        var number = pagination.number || vm.itemsPerPage; // Number of entries showed per page.
        var pageNumber = start / number + 1;
        Resource.getStorageMediums(start, number, pageNumber, tableState, sorting, search)
          .then(function(result) {
            vm.displayedMediums = result.data;
            tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
            $scope.ipLoading = false;
            $scope.initLoad = false;
            SelectedIPUpdater.update(vm.displayedMediums, [], $scope.storageMedium);
          })
          .catch(function(response) {
            if (response.status == 404) {
              var filters = {
                search: search,
              };

              listViewService.checkPages('storage_medium', number, filters).then(function(result) {
                tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
                tableState.pagination.start = result.numberOfPages * number - number;
                vm.callServer(tableState);
              });
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
        var sorting = tableState.sort;
        var pagination = tableState.pagination;
        var start = pagination.start || 0; // This is NOT the page number, but the index of item in the list that you want to use to display the table.
        var number = pagination.number || vm.objectsPerPage; // Number of entries showed per page.
        var pageNumber = start / number + 1;
        Resource.getStorageObjectsForMedium(
          $scope.storageMedium.id,
          start,
          number,
          pageNumber,
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
              var filters = {
                search: search,
              };

              listViewService.checkPages('storage_object', number, filters).then(function(result) {
                tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
                tableState.pagination.start = result.numberOfPages * number - number;
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
  });
