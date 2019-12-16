export default class RemoveValidationModalInstanceCtrl {
  constructor($uibModalInstance, data) {
    const $ctrl = this;
    $ctrl.data = data;
    $ctrl.remove = () => {
      $uibModalInstance.close('remove');
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
