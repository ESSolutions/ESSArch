export default class ActionDetailsModalInstanceCtrl {
  constructor($uibModalInstance, data) {
    const $ctrl = this;
    $ctrl.data = data;
    $ctrl.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
