angular
  .module('essarch.controllers')
  .controller('RemoveStructureUnitModalInstanceCtrl', function(
    data,
    $http,
    appConfig,
    Notifications,
    $uibModalInstance,
    $translate
  ) {
    var $ctrl = this;
    $ctrl.data = data;

    $ctrl.$onInit = function() {
      if (data.node) {
        $ctrl.node = data.node;
      }
    };

    $ctrl.removeNode = function() {
      $http
        .delete(appConfig.djangoUrl + 'structures/' + data.structure.id + '/units/' + $ctrl.node.id)
        .then(function(response) {
          Notifications.add($translate.instant('ACCESS.NODE_REMOVED'), 'success');
          $uibModalInstance.close($ctrl.node);
        });
    };

    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  });
