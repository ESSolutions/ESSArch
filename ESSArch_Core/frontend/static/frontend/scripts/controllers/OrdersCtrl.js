export default class {
  constructor(
    $scope,
    $controller,
    $rootScope,
    Resource,
    $timeout,
    appConfig,
    $http,
    $uibModal,
    $q,
    $log,
    SelectedIPUpdater,
    listViewService,
    $state,
    myService
  ) {
    const vm = this;
    $controller('BaseCtrl', {$scope: $scope, vm: vm, ipSortString: '', params: {}});

    vm.getOrderListColspan = function() {
      if (myService.checkPermission('ip.change_order') && myService.checkPermission('ip.delete_order')) {
        return 6;
      } else if (myService.checkPermission('ip.change_order') || myService.checkPermission('ip.delete_order')) {
        return 5;
      } else {
        return 4;
      }
    };

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
        } else {
          tableState.search = {
            predicateObject: {
              $: vm.initialSearch,
            },
          };
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.itemsPerPage);
        Resource.getOrders(
          paginationParams.start,
          paginationParams.number,
          paginationParams.pageNumber,
          tableState,
          sorting,
          search
        ).then(function(result) {
          vm.displayedIps = result.data;
          tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
          tableState.pagination.totalItemCount = result.count;
          $scope.ipLoading = false;
          SelectedIPUpdater.update(vm.displayedIps, $scope.ips, $scope.ip);
        });
      }
    };

    //Click function for Ip table
    $scope.ipTableClick = function(row, events, options) {
      if ($scope.select && $scope.ip.id == row.id) {
        $scope.select = false;
        $scope.eventlog = false;
        $scope.edit = false;
        $scope.requestForm = false;
        $scope.ip = null;
        $rootScope.ip = null;
        if (angular.isUndefined(options) || !options.noStateChange) {
          $state.go($state.current.name, {id: null});
        }
      } else {
        $scope.ip = row;
        $rootScope.ip = $scope.ip;
        if (angular.isUndefined(options) || !options.noStateChange) {
          $state.go($state.current.name, {id: $scope.ip.id});
        }
        $scope.select = true;
        $scope.eventlog = true;
        $scope.edit = true;
      }
      $scope.eventShow = false;
      $scope.statusShow = false;
    };
    vm.ips = [];
    vm.getIpsForOrder = function(order) {
      const ips = [];
      order.information_packages.forEach(function(ipUrl) {
        ips.push(
          $http.get(ipUrl).then(function(response) {
            return response.data;
          })
        );
      });
      $q.all(ips).then(function(response) {
        console.log(response);
        vm.ips = response;
      });
    };

    vm.ip = null;
    vm.openFilebrowser = function(ip) {
      if (vm.ip && vm.ip.id === ip.id) {
        vm.ip = null;
        $rootScope.ip = null;
      } else {
        vm.ip = ip;
        $rootScope.ip = ip;
      }
    };

    vm.ipPipe = function(tableState) {
      $scope.ipsLoading = true;
      if (vm.ips.length == 0) {
        $scope.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        const ips = [];
        $scope.ipTableState = tableState;
        $scope.ip.information_packages.forEach(function(ipUrl) {
          ips.push(
            $http.get(ipUrl).then(function(response) {
              return response.data;
            })
          );
        });
        $q.all(ips).then(function(response) {
          vm.ips = response;
          $scope.ipsLoading = false;
        });
      }
    };
    $scope.colspan = 9;
    $scope.stepTaskInfoShow = false;
    $scope.statusShow = false;
    $scope.eventShow = false;
    $scope.select = false;
    $scope.subSelect = false;
    $scope.edit = false;
    $scope.eventlog = false;
    $scope.requestForm = false;
    $scope.removeIp = function(order) {
      $http({
        method: 'DELETE',
        url: appConfig.djangoUrl + 'orders/' + order.id + '/',
      }).then(function() {
        vm.displayedIps.splice(vm.displayedIps.indexOf(order), 1);
        $scope.edit = false;
        $scope.select = false;
        $scope.eventlog = false;
        $scope.eventShow = false;
        $scope.statusShow = false;
        if (vm.displayedIps.length == 0) {
          $state.reload();
        }
        $scope.getListViewData();
      });
    };
    $scope.newOrderModal = function() {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/new-order-modal.html',
        scope: $scope,
        controller: 'OrderModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: {},
        },
      });
      modalInstance.result.then(function(data) {
        $timeout(function() {
          $scope.getListViewData();
        });
      });
    };

    $scope.editOrderModal = function(order) {
      console.log('order: ', order);
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/edit_order_modal.html',
        scope: $scope,
        controller: 'OrderModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: {
            order: order,
          },
        },
      });
      modalInstance.result.then(function(data) {
        $timeout(function() {
          $scope.getListViewData();
        });
      });
    };

    //Create and show modal for remove ip
    $scope.removeOrderModal = function(order) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove-order-modal.html',
        controller: 'OrderModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: function() {
            return {
              order: order,
              allow_close: true,
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $scope.select = false;
          $scope.getListViewData();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
  }
}
