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
along with this program. If not, see <http://www.gnu.org/licenses/>.

Contact information:
Web - http://www.essolutions.se
Email - essarch@essolutions.se
*/

export default class RobotInformationCtrl {
  constructor(
    StorageMedium,
    $scope,
    $controller,
    $interval,
    $rootScope,
    $http,
    Resource,
    appConfig,
    $timeout,
    $anchorScroll,
    $translate,
    Storage,
    $uibModal,
    listViewService,
    $transitions
  ) {
    const vm = this;
    $scope.translate = $translate;
    vm.slotsPerPage = 10;
    $scope.colspan = 4;
    vm.robots = [];
    $scope.select = false;
    vm.selectedRobot = null;
    vm.tapeDrive = null;
    vm.tapeSlot = null;
    vm.tapeSlots = [];
    vm.tapeDrives = [];
    vm.robotQueue = [];
    $scope.storageMediums = [];
    $scope.requestForm = false;
    $scope.eventlog = false;

    // Table states

    let robotInterval;
    $transitions.onSuccess({}, function($transition) {
      $interval.cancel(robotInterval);
    });
    $interval.cancel(robotInterval);
    robotInterval = $interval(function() {
      vm.updateTables();
    }, appConfig.robotInterval);

    vm.updateTables = function() {
      $scope.loadRobots(vm.robotTableState);
      if (vm.selectedRobot != null) {
        $scope.getRobotQueue(vm.robotQueueTableState);
        $scope.getSlots(vm.slotTableState);
        $scope.getDrives(vm.driveTableState);
      }
    };
    $scope.menuOptions = function(rowType) {
      return [];
    };

    $scope.initRequestData = function(types) {
      vm.requestTypes = types;
      vm.request = {
        type: types[0],
        purpose: '',
        storageMedium: null,
      };
    };

    // Getters
    $scope.getDrives = function(tableState) {
      if (!angular.isUndefined(tableState)) {
        vm.driveTableState = tableState;
        $scope.tapeDrivesLoading = true;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.drivesPerPage);
        Resource.getTapeDrives(
          paginationParams.start,
          paginationParams.number,
          paginationParams.pageNumber,
          tableState,
          sorting,
          search,
          vm.selectedRobot
        )
          .then(function(result) {
            vm.tapeDrives = result.data;
            tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
            $scope.tapeDrivesLoading = false;
          })
          .catch(function(response) {
            $scope.tapeDrivesLoading = false;
            if (response.status == 404) {
              const filters = {
                search: search,
              };

              listViewService.checkPages('tapedrive', paginationParams.number, filters).then(function(result) {
                tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
                tableState.pagination.start = result.numberOfPages * paginationParams.number - paginationParams.number;
                $scope.getDrives(tableState);
              });
            }
          });
      }
    };

    $scope.getSlots = function(tableState) {
      if (!angular.isUndefined(tableState)) {
        vm.slotTableState = tableState;
        $scope.tapeSlotsLoading = true;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.slotsPerPage);
        Resource.getTapeSlots(
          paginationParams.start,
          paginationParams.number,
          paginationParams.pageNumber,
          tableState,
          sorting,
          search,
          vm.selectedRobot
        )
          .then(function(result) {
            vm.tapeSlots = result.data;
            tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
            $scope.tapeSlotsLoading = false;
          })
          .catch(function(response) {
            $scope.tapeSlotsLoading = false;
            if (response.status == 404) {
              const filters = {
                search: search,
              };

              listViewService.checkPages('tapeslot', paginationParams.number, filters).then(function(result) {
                tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
                tableState.pagination.start = result.numberOfPages * paginationParams.number - paginationParams.number;
                $scope.getSlots(tableState);
              });
            }
          });
      }
    };

    $scope.getRobotQueue = function(tableState) {
      if (!angular.isUndefined(tableState)) {
        vm.robotQueueTableState = tableState;
        $scope.robotQueueLoading = true;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.robotQueueItemsPerPage);
        Resource.getRobotQueueForRobot(
          paginationParams.start,
          paginationParams.number,
          paginationParams.pageNumber,
          tableState,
          sorting,
          search,
          vm.selectedRobot
        )
          .then(function(result) {
            vm.robotQueue = result.data;
            tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
            $scope.robotQueueLoading = false;
          })
          .catch(function(response) {
            $scope.robotQueueLoading = false;
            if (response.status == 404) {
              const filters = {
                search: search,
              };

              listViewService
                .checkPages('robot_queue_for_robot', paginationParams.number, filters, vm.selectedRobot.id)
                .then(function(result) {
                  tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
                  tableState.pagination.start =
                    result.numberOfPages * paginationParams.number - paginationParams.number;
                  $scope.getRobotQueue(tableState);
                });
            }
          });
      }
    };

    $scope.loadRobots = function(tableState) {
      $scope.ipLoading = true;
      if (!angular.isUndefined(tableState)) {
        vm.robotTableState = tableState;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.robotsPerPage);
        Resource.getRobots(
          paginationParams.start,
          paginationParams.number,
          paginationParams.pageNumber,
          tableState,
          sorting,
          search
        )
          .then(function(result) {
            vm.robots = result.data;
            tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
            $scope.ipLoading = false;
          })
          .catch(function(response) {
            if (response.status == 404) {
              const filters = {
                search: search,
              };

              listViewService.checkPages('robot', paginationParams.number, filters).then(function(result) {
                tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
                tableState.pagination.start = result.numberOfPages * paginationParams.number - paginationParams.number;
                $scope.loadRobots(tableState);
              });
            } else {
              $scope.ipLoading = false;
            }
          });
      }
    };

    // Click funcitons

    $scope.robotClick = function(robot) {
      if ($scope.select && vm.selectedRobot.id == robot.id) {
        $scope.select = false;
        $scope.edit = false;
        vm.selectedRobot = null;
      } else {
        vm.selectedRobot = robot;
        $scope.select = true;
        $scope.getSlots(vm.slotTableState);
        $scope.getDrives(vm.driveTableState);
        $scope.getRobotQueue(vm.robotQueueTableState);
      }
    };

    vm.inventoryClick = function(robot) {
      $scope.initRequestData(['inventory']);
      requestModal(vm.request, robot);
    };

    vm.tapeDriveClick = function(tapeDrive) {
      if (tapeDrive == vm.tapeDrive) {
        vm.tapeDrive = null;
      } else {
        vm.tapeSlot = null;
        vm.tapeDrive = tapeDrive;
        const types = [];
        if (!tapeDrive.locked) {
          if (tapeDrive.storage_medium != null) {
            types.push('unmount');
          } else {
            types.push('mount');
          }
        } else {
          if (tapeDrive.storage_medium != null) {
            types.push('unmount_force');
          }
        }
        if (types.includes('mount')) {
          vm.getStorageMediumsByState(20).then(function(result) {
            $scope.storageMediums = result;
          });
        }
        $scope.initRequestData(types);
        requestModal(vm.request, vm.tapeDrive);
      }
    };

    vm.tapeSlotClick = function(tapeSlot) {
      if (tapeSlot.medium_id === '') {
        return;
      }
      if (tapeSlot == vm.tapeSlot) {
        vm.tapeSlot = null;
      } else {
        vm.tapeDrive = null;
        vm.tapeSlot = tapeSlot;
        const types = [];
        if (!tapeSlot.locked) {
          if (tapeSlot.mounted) {
            types.push('unmount');
          } else {
            types.push('mount');
          }
        } else {
          if (tapeSlot.mounted) {
            types.push('unmount_force');
          }
        }
        $scope.initRequestData(types);
        requestModal(vm.request, vm.tapeSlot);
      }
    };

    vm.getStorageMediumsByState = function(status) {
      return StorageMedium.query({status: status}).$promise.then(function(data) {
        return data;
      });
    };

    // Actions
    vm.inventoryRobot = function(robot, request) {
      Storage.inventoryRobot(robot).then(function(result) {
        $scope.requestForm = false;
        $scope.eventlog = false;
      });
    };

    vm.mountTapeDrive = function(tapeDrive, request) {
      Storage.mountTapeDrive(tapeDrive, request.storageMedium).then(function() {
        $scope.requestForm = false;
        $scope.eventlog = false;
      });
    };

    vm.unmountTapeDrive = function(tapeDrive, request, force) {
      Storage.unmountTapeDrive(tapeDrive, force).then(function() {
        $scope.requestForm = false;
        $scope.eventlog = false;
      });
    };

    vm.mountTapeSlot = function(tapeSlot, request) {
      Storage.mountTapeSlot(tapeSlot, request).then(function() {
        $scope.requestForm = false;
        $scope.eventlog = false;
      });
    };

    vm.unmountTapeSlot = function(tapeSlot, request, force) {
      Storage.unmountTapeSlot(tapeSlot, force).then(function() {
        $scope.requestForm = false;
        $scope.eventlog = false;
      });
    };
    // Requests
    $scope.submitRequest = function(object, request) {
      switch (request.type) {
        case 'inventory':
          vm.inventoryRobot(object, request);
          break;
        case 'mount':
          if (vm.tapeDrive != null) {
            vm.mountTapeDrive(vm.tapeDrive, request);
          } else if (vm.tapeSlot != null) {
            vm.mountTapeSlot(vm.tapeSlot, request);
          }
          break;
        case 'unmount':
          if (vm.tapeDrive != null) {
            vm.unmountTapeDrive(vm.tapeDrive, request, false);
          } else if (vm.tapeSlot != null) {
            vm.unmountTapeSlot(vm.tapeSlot, request, false);
          }
          break;
        case 'unmount_force':
          if (vm.tapeDrive != null) {
            vm.unmountTapeDrive(vm.tapeDrive, request, true);
          } else if (vm.tapeSlot != null) {
            vm.unmountTapeSlot(vm.tapeSlot, request, true);
          }
          break;
      }
    };

    function requestModal(request, object) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/request-modal.html',
        controller: 'RequestModalInstanceCtrl',
        scope: $scope,
        controllerAs: '$ctrl',
        resolve: {
          data: function() {
            return {
              request: request,
              types: vm.requestTypes,
              object: object,
            };
          },
        },
      });
      modalInstance.result.then(function(data) {
        if (vm.tapeDrive && data.id == vm.tapeDrive.id) {
          vm.tapeDrive = null;
        } else if (vm.tapeSlot && data.id == vm.tapeSlot.id) {
          vm.tapeSlot = null;
        }
      });
    }

    $scope.closeRequestForm = function() {
      $scope.requestForm = false;
      $scope.eventlog = false;
      vm.tapeDrive = null;
      vm.tapeSlot = null;
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

    // Click function for request form submit.
    // Replaced form="vm.requestForm" to work in IE
    $scope.clickSubmit = function() {
      if (vm.requestForm.$valid) {
        $scope.submitRequest(vm.selectedRobot, vm.request);
      }
    };
  }
}
