export default class RequestModalInstanceCtrl {
  constructor($uibModalInstance, data, $scope) {
    var $ctrl = this;
    $ctrl.angular = angular;
    $ctrl.object = data.object;
    $ctrl.requestTypes = data.types;
    $ctrl.request = data.request;
    $ctrl.submit = function() {
      $scope.submitRequest($ctrl.object, $ctrl.request);
      $uibModalInstance.close($ctrl.object);
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
