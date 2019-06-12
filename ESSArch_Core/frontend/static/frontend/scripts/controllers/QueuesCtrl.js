export default class QueuesCtrl {
  constructor(appConfig, $scope, $rootScope, Storage, Resource, $interval, $transitions) {
    var vm = this;
    $scope.select = true;
    vm.ioQueue = [];
    vm.robotQueue = [];
    vm.robotsPerPage = 10;
    vm.ioPerPage = 10;
    var ioInterval;
    $interval.cancel(ioInterval);
    ioInterval = $interval(function() {
      vm.getIoQueue(vm.ioTableState);
    }, appConfig.queueInterval);

    var robotInterval;
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
        vm.ioTableState = tableState;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        var sorting = tableState.sort;
        var pagination = tableState.pagination;
        var start = pagination.start || 0; // This is NOT the page number, but the index of item in the list that you want to use to display the table.
        var number = pagination.number || vm.ioPerPage; // Number of entries showed per page.
        var pageNumber = start / number + 1;
        Resource.getIoQueue(start, number, pageNumber, tableState, sorting, search)
          .then(function(result) {
            vm.ioQueue = result.data;
            tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
          })
          .catch(function(response) {
            if (response.status == 404) {
              var filters = {
                search: search,
              };

              listViewService.checkPages('io_queue', number, filters).then(function(result) {
                tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
                tableState.pagination.start = result.numberOfPages * number - number;
                $scope.getIoQueue(tableState);
              });
            }
          });
      }
    };

    vm.getRobotQueue = function(tableState) {
      if (!angular.isUndefined(tableState)) {
        vm.robotTableState = tableState;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        var sorting = tableState.sort;
        var pagination = tableState.pagination;
        var start = pagination.start || 0; // This is NOT the page number, but the index of item in the list that you want to use to display the table.
        var number = pagination.number || vm.robotsPerPage; // Number of entries showed per page.
        var pageNumber = start / number + 1;
        Resource.getRobotQueue(start, number, pageNumber, tableState, sorting, search)
          .then(function(result) {
            vm.robotQueue = result.data;
            tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
          })
          .catch(function(response) {
            if (response.status == 404) {
              var filters = {
                search: search,
              };

              listViewService.checkPages('robot_queue', number, filters).then(function(result) {
                tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
                tableState.pagination.start = result.numberOfPages * number - number;
                $scope.getIoQueue(tableState);
              });
            }
          });
      }
    };
  }
}
