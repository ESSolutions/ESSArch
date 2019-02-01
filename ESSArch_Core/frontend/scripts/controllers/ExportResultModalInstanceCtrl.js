angular
  .module('essarch.controllers')
  .controller('ExportResultModalInstanceCtrl', function(
    $translate,
    $uibModalInstance,
    djangoAuth,
    appConfig,
    $http,
    data,
    $scope,
    Notifications,
    $timeout,
    Search,
    $sce,
    $window
  ) {
    var $ctrl = this;
    var vm = data.vm;
    $ctrl.formats = ['pdf', 'csv'];
    $ctrl.format = 'pdf';
    $ctrl.exporting = false;
    $ctrl.export = function() {
      var file = $sce.trustAsResourceUrl(vm.getExportResultUrl(vm.tableState, $ctrl.format));
      $window.open(file, '_blank');
      $uibModalInstance.close();
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  });
