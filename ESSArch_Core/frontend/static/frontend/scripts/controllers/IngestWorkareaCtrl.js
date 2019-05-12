angular
  .module('essarch.controllers')
  .controller('IngestWorkareaCtrl', function(
    WorkareaFiles,
    Workarea,
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
    $state,
    $http,
    listViewService,
    Requests,
    $uibModal,
    $sce,
    $window
  ) {
    var vm = this;
    var ipSortString = [];
    vm.workarea = 'ingest';

    $controller('WorkareaCtrl', {$scope: $scope, vm: vm, ipSortString: ipSortString});
  });
