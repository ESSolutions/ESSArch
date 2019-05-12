angular
  .module('essarch.controllers')
  .controller('OrdersCtrl', function(
    $scope,
    $controller,
    $rootScope,
    Resource,
    $interval,
    $timeout,
    appConfig,
    $cookies,
    $anchorScroll,
    $translate,
    $http,
    $uibModal,
    listViewService,
    $q,
    $log,
    SelectedIPUpdater
  ) {
    var vm = this;
    $controller('BaseCtrl', {$scope: $scope, vm: vm, ipSortString: ''});

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
        var sorting = tableState.sort;
        var pagination = tableState.pagination;
        var start = pagination.start || 0; // This is NOT the page number, but the index of item in the list that you want to use to display the table.
        var number = pagination.number || vm.itemsPerPage; // Number of entries showed per page.
        var pageNumber = start / number + 1;
        Resource.getOrders(start, number, pageNumber, tableState, sorting, search).then(function(result) {
          vm.displayedIps = result.data;
          tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
          $scope.ipLoading = false;
          SelectedIPUpdater.update(vm.displayedIps, $scope.ips, $scope.ip);
        });
      }
    };

    //Click function for Ip table
    $scope.ipTableClick = function(row) {
      if ($scope.select && $scope.ip.id == row.id) {
        $scope.select = false;
        $scope.eventlog = false;
        $scope.edit = false;
        $scope.requestForm = false;
        $scope.ip = null;
        $rootScope.ip = null;
      } else {
        $scope.ip = row;
        $rootScope.ip = $scope.ip;
        $scope.select = true;
        $scope.eventlog = true;
        $scope.edit = true;
      }
      $scope.eventShow = false;
      $scope.statusShow = false;
    };
    vm.ips = [];
    vm.getIpsForOrder = function(order) {
      var ips = [];
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
        var ips = [];
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
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/new-order-modal.html',
        scope: $scope,
        controller: 'OrderModalInstanceCtrl',
        controllerAs: '$ctrl',
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

    //Create and show modal for remove ip
    $scope.removeOrderModal = function(order) {
      var modalInstance = $uibModal.open({
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
  });
