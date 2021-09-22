export default class ActionDetailsModalInstanceCtrl {
  constructor($uibModalInstance, $translate, data) {
    const $ctrl = this;
    $ctrl.data = data;
    $ctrl.flowOptions = {};

    $ctrl.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };
    $ctrl.purposeField = [
      {
        key: 'purpose',
        type: 'input',
        templateOptions: {
          label: $translate.instant('PURPOSE'),
        },
      },
    ];
  }
}
