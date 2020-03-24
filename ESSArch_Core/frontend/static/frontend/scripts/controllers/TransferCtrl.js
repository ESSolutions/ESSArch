export default class TransferCtrl {
  constructor(
    $scope,
    appConfig,
    $http,
    $uibModal,
    $log,
    $translate,
    myService,
    $state,
    $stateParams,
    listViewService,
    $transitions
  ) {
    const vm = this;
    $scope.$translate = $translate;
    vm.selectedTransfer = null;
    vm.initialSearch = null;
    vm.transfers = [];
    vm.types = [];
    vm.tags = [];
    vm.units = [];

    vm.accordion = {
      basic: {open: false},
      events: {open: true},
      nodes: {open: true},
      units: {open: true},
    };

    let watchers = [];
    watchers.push(
      $transitions.onSuccess({}, function ($transition) {
        if ($transition.from().name !== $transition.to().name) {
          watchers.forEach(function (watcher) {
            watcher();
          });
        } else {
          let params = $transition.params();
          if (
            params.transfer !== null &&
            (vm.selectedTransfer === null || params.transfer !== vm.selectedTransfer.id)
          ) {
            vm.initialSearch = params.transfer;
            $http.get(appConfig.djangoUrl + 'transfers/' + params.transfer + '/').then(function (response) {
              vm.transferClick(response.data);
              vm.initLoad = false;
            });
          } else if (params.transfer === null && vm.selectedTransfer !== null) {
            vm.transferClick(vm.selectedTransfer);
          }
        }
      })
    );

    vm.$onInit = function () {
      vm.initLoad = true;
      vm.delivery = $stateParams.delivery;
      if (
        !angular.isUndefined($stateParams.transfer) &&
        $stateParams.transfer !== null &&
        $stateParams.transfer !== ''
      ) {
        vm.initialSearch = $stateParams.transfer;
        $http
          .get(appConfig.djangoUrl + 'transfers/' + $stateParams.transfer + '/')
          .then(function (response) {
            vm.transferClick(response.data);
            vm.initLoad = false;
          })
          .catch(function (response) {
            vm.selectedTransfer = null;
            $state.go($state.current.name, {transfer: null, delivery: vm.delivery});
          });
      } else {
        vm.initLoad = false;
      }
    };

    vm.transferClick = function (transfer) {
      if (vm.selectedTransfer !== null && transfer.id === vm.selectedTransfer.id) {
        vm.selectedTransfer = null;
        $state.go($state.current.name, {transfer: null});
      } else {
        vm.selectedTransfer = transfer;
        if ($stateParams.id !== transfer.id) {
          $state.go($state.current.name, {transfer: transfer.id});
        }
        vm.transferEventsPipe(vm.transferEventsTableState);
        vm.tagsPipe(vm.tagsTableState);
        vm.unitsPipe(vm.unitsTableState);
      }
    };

    vm.transferPipe = function (tableState) {
      if (vm.transfers.length == 0) {
        $scope.initLoad = true;
      }
      vm.transfersLoading = true;
      if (!angular.isUndefined(tableState)) {
        vm.transferTableState = tableState;
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
        vm.getTransfers({
          page: paginationParams.pageNumber,
          page_size: paginationParams.number,
          ordering: sortString,
          search: search,
        }).then(function (response) {
          tableState.pagination.numberOfPages = Math.ceil(response.headers('Count') / paginationParams.number); //set the number of pages so the pagination can update
          $scope.initLoad = false;
          vm.transfersLoading = false;
          vm.transfers = response.data;
        });
      }
    };

    vm.getTransfers = function (params) {
      return $http
        .get(appConfig.djangoUrl + 'deliveries/' + vm.delivery + '/transfers/', {params: params})
        .then(function (response) {
          return response;
        });
    };

    vm.tagsPipe = function (tableState) {
      vm.tagsLoading = true;
      if (angular.isUndefined(vm.tags) || vm.tags.length == 0) {
        $scope.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        vm.tagsTableState = tableState;
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

        vm.getTags(vm.selectedTransfer, {
          page: pageNumber,
          page_size: number,
          ordering: sortString,
          search: search,
        }).then(function (response) {
          tableState.pagination.numberOfPages = Math.ceil(response.headers('Count') / number); //set the number of pages so the pagination can update
          $scope.initLoad = false;
          vm.tagsLoading = false;
          vm.tags = response.data;
        });
      }
    };

    vm.getTags = function (transfer, params) {
      return $http
        .get(appConfig.djangoUrl + 'transfers/' + transfer.id + '/tags/', {params: params})
        .then(function (response) {
          return response;
        });
    };

    vm.unitsPipe = function (tableState) {
      vm.unitsLoading = true;
      if (angular.isUndefined(vm.units) || vm.units.length == 0) {
        $scope.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        vm.unitsTableState = tableState;
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

        vm.getUnits(vm.selectedTransfer, {
          page: pageNumber,
          page_size: number,
          ordering: sortString,
          search: search,
        }).then(function (response) {
          tableState.pagination.numberOfPages = Math.ceil(response.headers('Count') / number); //set the number of pages so the pagination can update
          $scope.initLoad = false;
          vm.unitsLoading = false;
          vm.units = response.data;
        });
      }
    };

    vm.getUnits = function (transfer, params) {
      return $http
        .get(appConfig.djangoUrl + 'transfers/' + transfer.id + '/structure-units/', {params: params})
        .then(function (response) {
          return response;
        });
    };

    vm.transferEventsPipe = function (tableState) {
      vm.transferEventsLoading = true;
      if (angular.isUndefined(vm.transferEvents) || vm.transferEvents.length == 0) {
        $scope.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        vm.transferEventsTableState = tableState;
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

        vm.getTransferEvents(vm.selectedTransfer, {
          page: pageNumber,
          page_size: number,
          ordering: sortString,
          search: search,
        }).then(function (response) {
          tableState.pagination.numberOfPages = Math.ceil(response.headers('Count') / number); //set the number of pages so the pagination can update
          $scope.initLoad = false;
          vm.transferEventsLoading = false;
          vm.transferEvents = response.data;
        });
      }
    };

    vm.getTransferEvents = function (transfer, params) {
      return $http
        .get(appConfig.djangoUrl + 'transfers/' + transfer.id + '/events/', {params: params})
        .then(function (response) {
          return response;
        });
    };

    vm.getTransferColspan = function () {
      if (myService.checkPermission('tags.change_transfer') && myService.checkPermission('tags.delete_transfer')) {
        return 3;
      } else if (
        myService.checkPermission('tags.change_transfer') ||
        myService.checkPermission('tags.delete_transfer')
      ) {
        if (!myService.checkPermission('tags.change_transfer')) {
          return 2;
        } else {
          return 1;
        }
      } else {
        return 2;
      }
    };

    vm.getNodeColspan = function () {
      if (myService.checkPermission('tags.change_transfer')) {
        return 4;
      } else {
        return 3;
      }
    };

    vm.getEventColspan = function () {
      if (myService.checkPermission('ip.change_eventip') && myService.checkPermission('ip.delete_eventip')) {
        return 6;
      } else if (myService.checkPermission('ip.change_eventip') || myService.checkPermission('ip.delete_eventip')) {
        return 5;
      } else {
        return 4;
      }
    };

    // Transfers
    vm.createTransferModal = function () {
      const data = {};
      if ($stateParams.delivery) {
        data.delivery = $stateParams.delivery;
      }
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/new_transfer_modal.html',
        controller: 'TransferModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function () {
            return data;
          },
        },
      });
      modalInstance.result.then(
        function (data) {
          vm.transferPipe(vm.transferTableState);
          vm.transferClick(data);
        },
        function () {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.editTransferModal = function (transfer) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/edit_transfer_modal.html',
        controller: 'TransferModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function () {
            return {
              transfer: transfer,
            };
          },
        },
      });
      modalInstance.result.then(
        function (data) {
          vm.transferPipe(vm.transferTableState);
        },
        function () {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.viewTransferModal = function (transfer) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/view_transfer_modal.html',
        controller: 'TransferModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function () {
            return {
              transfer: transfer,
            };
          },
        },
      });
      modalInstance.result.then(
        function (data) {
          vm.transferPipe(vm.transferTableState);
        },
        function () {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.removeTransferModal = function (transfer) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_transfer_modal.html',
        controller: 'TransferModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function () {
            return {
              transfer: transfer,
              allow_close: true,
              remove: true,
            };
          },
        },
      });
      modalInstance.result.then(
        function (data) {
          vm.selectedTransfer = null;
          vm.transferPipe(vm.transferTableState);
        },
        function () {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.createEventModal = function (params) {
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
          data: function () {
            return data;
          },
        },
      });
      modalInstance.result.then(
        function (data) {
          if (params.transfer) {
            vm.transferPipe(vm.transferTableState);
            vm.transferEventsPipe(vm.transferEventsTableState);
          }
          if (params.delivery && !params.transfer) {
            vm.deliveryPipe(vm.tableState);
            vm.deliveryEventsPipe(vm.deliveryEventsTableState);
          }
        },
        function () {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.editEventModal = function (event, params) {
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
          data: function () {
            return data;
          },
        },
      });
      modalInstance.result.then(
        function (data) {
          if (vm.activeTab === 'events') {
            vm.deliveryPipe(vm.tableState);
            vm.deliveryEventsPipe(vm.deliveryEventsTableState);
          } else {
            vm.transferPipe(vm.transferTableState);
            vm.transferEventsPipe(vm.transferEventsTableState);
          }
        },
        function () {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.removeEventModal = function (event) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_event_modal.html',
        controller: 'EventModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function () {
            return {
              event: event,
            };
          },
        },
      });
      modalInstance.result.then(
        function (data) {
          if (vm.activeTab === 'events') {
            vm.deliveryPipe(vm.tableState);
            vm.deliveryEventsPipe(vm.deliveryEventsTableState);
          } else {
            vm.transferPipe(vm.transferTableState);
            vm.transferEventsPipe(vm.transferEventsTableState);
          }
        },
        function () {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.removeLinkModal = function (node) {
      let data;
      if (angular.isArray(node)) {
        data = {
          nodes: node,
        };
      } else {
        data = {
          node: node,
        };
      }
      data.allow_close = true;
      data.transfer = vm.selectedTransfer;
      data.remove_link = true;
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_node_transfer_link_modal.html',
        size: 'lg',
        controller: 'NodeTransferModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: data,
        },
      });
      modalInstance.result.then(
        function (data) {
          vm.tagsPipe(vm.tagsTableState);
          vm.unitsPipe(vm.unitsTableState);
        },
        function () {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
  }
}
