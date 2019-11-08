export default class ConfirmReceiveCtrl {
  constructor(IPReception, Notifications, $uibModalInstance, data) {
    const $ctrl = this;

    $ctrl.receiving = false;
    if (data) {
      $ctrl.data = data;
    }
    $ctrl.receive = function(ip) {
      $ctrl.receiving = true;
      let requestData = {
        id: ip.id,
        storage_policy: data.request.storagePolicy.value.id,
        purpose: data.request.purpose,
        structure_unit: data.structure_unit,
        validators: data.validatorModel,
      };
      if (data.archive) {
        requestData.archive = data.archive;
      }
      if (data.structure) {
        requestData.structure = data.structure;
      }
      return IPReception.receive(requestData)
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
