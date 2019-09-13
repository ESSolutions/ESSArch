export default class DeliveryCtrl {
  constructor(
    $scope,
    appConfig,
    $http,
    $timeout,
    $uibModal,
    $log,
    listViewService,
    $translate,
    myService,
    $state,
    $stateParams,
    AgentName
  ) {
    const vm = this;
    $scope.AgentName = AgentName;
    $scope.$translate = $translate;
    vm.selected = null;
    vm.initialSearch = null;
    vm.deliveries = [];
    vm.transfers = [];
    vm.types = [];
    vm.tags = [];
    vm.units = [];

    vm.$onInit = function() {
      vm.initLoad = true;
      listViewService.getEventlogData().then(function(types) {
        vm.types = types;
        if (
          !angular.isUndefined($stateParams.delivery) &&
          $stateParams.delivery !== null &&
          $stateParams.delivery !== ''
        ) {
          vm.initialSearch = $stateParams.delivery;
          $http
            .get(appConfig.djangoUrl + 'deliveries/' + $stateParams.delivery + '/')
            .then(function(response) {
              vm.deliveryClick(response.data);
              vm.initLoad = false;
              if (angular.copy($state.current.name.split('.')).pop() === 'transfers') {
                $timeout(function() {
                  vm.activeTab = 'transfers';

                  $state.go('home.archivalDescriptions.deliveries.transfers', {
                    transfer: $stateParams.transfer,
                    delivery: $stateParams.delivery,
                  });
                });
              }
            })
            .catch(function(response) {
              vm.selected = null;
              $state.go($state.current.name, {delivery: null});
            });
        } else {
          vm.initLoad = false;
        }
      });
    };

    vm.mapEventType = function(type) {
      let mapped = type;
      vm.types.forEach(function(x) {
        if (x.eventType === type) {
          mapped = x.eventDetail;
        }
      });
      return mapped;
    };

    vm.eventsClick = function(event) {
      if (event.transfer) {
        vm.activeTab = 'transfers';
        $timeout(function() {
          $state.go('home.archivalDescriptions.deliveries.transfers', {
            delivery: vm.selected.id,
            transfer: event.transfer.id,
          });
        });
      }
    };

    vm.deliveryClick = function(delivery) {
      if (vm.selected !== null && delivery.id === vm.selected.id) {
        vm.selected = null;
        $state.go('home.archivalDescriptions.deliveries', {delivery: null});
      } else {
        vm.selected = null;
        $timeout(function() {
          vm.activeTab = 'events';
          vm.selectedTransfer = null;
          vm.selected = delivery;
          if ($stateParams.delivery !== delivery.id) {
            $state.go('home.archivalDescriptions.deliveries', {delivery: delivery.id});
          }
        });
      }
    };

    vm.tabClick = function(tab) {
      $timeout(function() {
        if (tab === 'transfers') {
          $state.go('home.archivalDescriptions.deliveries.transfers', {delivery: vm.selected.id});
        } else {
          $state.go('home.archivalDescriptions.deliveries', {delivery: vm.selected.id, transfer: null});
        }
      });
    };

    vm.deliveryPipe = function(tableState) {
      if (vm.deliveries.length == 0) {
        $scope.initLoad = true;
      }
      vm.deliveriesLoading = true;
      if (!angular.isUndefined(tableState)) {
        vm.tableState = tableState;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        } else {
          tableState.search = {
            predicateObject: {
              $: vm.initialSearch,
            },
          };
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        let sortString = sorting.predicate;
        if (sorting.reverse) {
          sortString = '-' + sortString;
        }

        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.itemsPerPage);
        vm.getDeliveries({
          page: paginationParams.pageNumber,
          page_size: paginationParams.number,
          ordering: sortString,
          search: search,
        }).then(function(response) {
          tableState.pagination.numberOfPages = Math.ceil(response.headers('Count') / paginationParams.number); //set the number of pages so the pagination can update
          $scope.initLoad = false;
          vm.deliveriesLoading = false;
          vm.deliveries = response.data;
        });
      }
    };

    vm.getDeliveries = function(params) {
      return $http.get(appConfig.djangoUrl + 'deliveries/', {params: params}).then(function(response) {
        return response;
      });
    };

    vm.deliveryEventsPipe = function(tableState) {
      vm.deliveryEventsLoading = true;
      if (angular.isUndefined(vm.deliveryEvents) || vm.deliveryEvents.length == 0) {
        $scope.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        vm.deliveryEventsTableState = tableState;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        const pagination = tableState.pagination;
        const start = pagination.start || 0; // This is NOT the page number, but the index of item in the list that you want to use to display the table.
        const number = pagination.number || vm.itemsPerPage; // Number of entries showed per page.
        const pageNumber = start / number + 1;

        let sortString = sorting.predicate;
        if (sorting.reverse) {
          sortString = '-' + sortString;
        }

        vm.getDeliveryEvents(vm.selected, {
          page: pageNumber,
          page_size: number,
          ordering: sortString,
          search: search,
        }).then(function(response) {
          tableState.pagination.numberOfPages = Math.ceil(response.headers('Count') / number); //set the number of pages so the pagination can update
          $scope.initLoad = false;
          vm.deliveryEventsLoading = false;
          vm.deliveryEvents = response.data;
        });
      }
    };

    vm.getDeliveryEvents = function(delivery, params) {
      return $http
        .get(appConfig.djangoUrl + 'deliveries/' + delivery.id + '/events/', {params: params})
        .then(function(response) {
          return response;
        });
    };

    vm.getDeliveryColspan = function() {
      if (myService.checkPermission('tags.change_delivery') && myService.checkPermission('tags.delete_delivery')) {
        return 8;
      } else if (
        myService.checkPermission('tags.change_delivery') ||
        myService.checkPermission('tags.delete_delivery')
      ) {
        return 7;
      } else {
        return 6;
      }
    };

    vm.getEventColspan = function() {
      if (myService.checkPermission('ip.change_eventip') && myService.checkPermission('ip.delete_eventip')) {
        return 7;
      } else if (myService.checkPermission('ip.change_eventip') || myService.checkPermission('ip.delete_eventip')) {
        return 6;
      } else {
        return 5;
      }
    };

    vm.createModal = function() {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/new_delivery_modal.html',
        controller: 'DeliveryModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return {};
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          vm.selected = data;
          vm.deliveryPipe(vm.tableState);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.editModal = function(delivery) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/edit_delivery_modal.html',
        controller: 'DeliveryModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return {
              delivery: delivery,
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          vm.deliveryPipe(vm.tableState);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.removeModal = function(delivery) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_delivery_modal.html',
        controller: 'DeliveryModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return {
              delivery: delivery,
              allow_close: true,
              remove: true,
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          vm.selected = null;
          vm.deliveryPipe(vm.tableState);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.createEventModal = function(params) {
      const data = {};
      if (params.transfer) {
        data.transfer = params.transfer;
      }
      if (params.delivery) {
        data.delivery = params.delivery;
      }
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/new_event_modal.html',
        controller: 'EventModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return data;
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          if (params.transfer) {
            vm.transferPipe(vm.transferTableState);
            vm.transferEventsPipe(vm.transferEventsTableState);
          }
          if (params.delivery && !params.transfer) {
            vm.deliveryPipe(vm.tableState);
            vm.deliveryEventsPipe(vm.deliveryEventsTableState);
          }
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.editEventModal = function(event, params) {
      const data = {
        event: event,
      };
      if (params.transfer) {
        data.transfer = params.transfer;
      }
      if (params.delivery) {
        data.delivery = params.delivery;
      }
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/edit_event_modal.html',
        controller: 'EventModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return data;
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          if (vm.activeTab === 'events') {
            vm.deliveryPipe(vm.tableState);
            vm.deliveryEventsPipe(vm.deliveryEventsTableState);
          } else {
            vm.transferPipe(vm.transferTableState);
            vm.transferEventsPipe(vm.transferEventsTableState);
          }
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.removeEventModal = function(event) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_event_modal.html',
        controller: 'EventModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return {
              event: event,
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          if (vm.activeTab === 'events') {
            vm.deliveryPipe(vm.tableState);
            vm.deliveryEventsPipe(vm.deliveryEventsTableState);
          } else {
            vm.transferPipe(vm.transferTableState);
            vm.transferEventsPipe(vm.transferEventsTableState);
          }
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
  }
}
