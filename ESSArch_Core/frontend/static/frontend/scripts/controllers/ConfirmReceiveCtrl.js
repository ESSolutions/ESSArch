angular
  .module('essarch.controllers')
  .controller('ConfirmReceiveCtrl', function(
    IPReception,
    Notifications,
    $uibModalInstance,
    data,
    $scope,
    $controller
  ) {
    var $ctrl = this;

    $ctrl.receiving = false;
    if (data) {
      $ctrl.data = data;
    }
    $ctrl.receive = function(ip) {
      $ctrl.receiving = true;
      return IPReception.receive({
        id: ip.id,
        archive_policy: data.request.archivePolicy.value.id,
        purpose: data.request.purpose,
        tag: data.tag,
        allow_unknown_files: data.request.allowUnknownFiles,
        validators: data.validatorModel,
      })
        .$promise.then(function(response) {
          Notifications.add(response.detail, 'success', 3000);
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
  });
