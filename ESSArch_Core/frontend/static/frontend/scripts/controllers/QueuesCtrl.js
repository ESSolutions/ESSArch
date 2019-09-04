export default class QueuesCtrl {
  constructor(appConfig, $scope, $rootScope, Storage, Resource, $interval, $transitions, listViewService) {
    const vm = this;
    $scope.select = true;
    vm.ioQueue = [];
    vm.robotQueue = [];
    vm.robotsPerPage = 10;
    vm.ioPerPage = 10;
    let ioInterval;
    $interval.cancel(ioInterval);
    ioInterval = $interval(function() {
      vm.getIoQueue(vm.ioTableState);
    }, appConfig.queueInterval);

    let robotInterval;
    $interval.cancel(robotInterval);
    robotInterval = $interval(function() {
      vm.getRobotQueue(vm.robotTableState);
    }, appConfig.queueInterval);

    $transitions.onSuccess({}, function($transition) {
      $interval.cancel(ioInterval);
      $interval.cancel(robotInterval);
    });

    vm.getIoQueue = function(tableState) {
      if (!angular.isUndefined(tableState)) {
        vm.ioLoading = true;
        vm.ioTableState = tableState;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.ioPerPage);
        Resource.getIoQueue(
          paginationParams.start,
          paginationParams.number,
          paginationParams.pageNumber,
          tableState,
          sorting,
          search
        )
          .then(function(result) {
            vm.ioQueue = result.data;
            tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
            vm.ioLoading = false;
          })
          .catch(function(response) {
            if (response.status == 404) {
              const filters = {
                search: search,
              };

              listViewService.checkPages('io_queue', paginationParams.number, filters).then(function(result) {
                tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
                tableState.pagination.start = result.numberOfPages * paginationParams.number - paginationParams.number;
                $scope.getIoQueue(tableState);
              });
            }
            vm.ioLoading = false;
          });
      }
    };

    vm.getRobotQueue = function(tableState) {
      if (!angular.isUndefined(tableState)) {
        vm.robotTableState = tableState;
        vm.robotLoading = true;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.robotsPerPage);
        Resource.getRobotQueue(
          paginationParams.start,
          paginationParams.number,
          paginationParams.pageNumber,
          tableState,
          sorting,
          search
        )
          .then(function(result) {
            vm.robotQueue = result.data;
            tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
            vm.robotLoading = false;
          })
          .catch(function(response) {
            if (response.status == 404) {
              const filters = {
                search: search,
              };

              listViewService.checkPages('robot_queue', paginationParams.number, filters).then(function(result) {
                tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
                tableState.pagination.start = result.numberOfPages * paginationParams.number - paginationParams.number;
                $scope.getIoQueue(tableState);
              });
            }
            vm.robotLoading = false;
          });
      }
    };
  }
}
