export default class RemoveStructureModalInstanceCtrl {
  constructor(data, Notifications, $uibModalInstance, $translate, Structure) {
    var $ctrl = this;
    $ctrl.data = data;

    $ctrl.$onInit = function() {
      if (data.node) {
        $ctrl.node = data.node;
      }
    };

    $ctrl.removing = false;
    $ctrl.remove = function(structure) {
      $ctrl.removing = true;
      Structure.remove({id: structure.id}).$promise.then(function(response) {
        $ctrl.removing = false;
        Notifications.add($translate.instant('ACCESS.CLASSIFICATION_STRUCTURE_REMOVED'), 'success');
        $uibModalInstance.close();
      });
    };

    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
