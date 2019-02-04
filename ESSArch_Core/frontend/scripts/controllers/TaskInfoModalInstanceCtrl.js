angular
  .module('essarch.controllers')
  .controller('TaskInfoModalInstanceCtrl', function(
    $uibModalInstance,
    djangoAuth,
    data,
    $http,
    Notifications,
    IP,
    appConfig,
    listViewService,
    $scope,
    $rootScope
  ) {
    var $ctrl = this;
    if (data) {
      $ctrl.data = data;
    }
    $ctrl.tracebackCopied = false;
    $ctrl.copied = function() {
      $ctrl.tracebackCopied = true;
    };
    $ctrl.idCopied = false;
    $ctrl.idCopyDone = function() {
      $ctrl.idCopied = true;
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
    $ctrl.mapStepStateProgress = $rootScope.mapStepStateProgress;
  });
