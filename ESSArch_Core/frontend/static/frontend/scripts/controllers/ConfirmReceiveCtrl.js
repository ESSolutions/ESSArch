export default class ConfirmReceiveCtrl {
  constructor(IPReception, Notifications, $uibModalInstance, data) {
    const $ctrl = this;

    $ctrl.receiving = false;
    if (data) {
      $ctrl.data = data;
    }
    $ctrl.receive = function(ip) {
      $ctrl.receiving = true;
      return IPReception.receive({
        id: ip.id,
        storage_policy: data.request.storagePolicy.value.id,
        purpose: data.request.purpose,
        structure_unit: data.structure_unit,
        allow_unknown_files: data.request.allowUnknownFiles,
        validators: data.validatorModel,
      })
        .$promise.then(function(response) {
          $ctrl.data = {received: true, status: 'received'};
          $ctrl.receiving = false;
          $uibModalInstance.close($ctrl.data);
        })
        .catch(function(response) {
          $ctrl.receiving = false;
          $ctrl.data = {received: false, status: 'error'};
          $uibModalInstance.dismiss($ctrl.data);
        });
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
