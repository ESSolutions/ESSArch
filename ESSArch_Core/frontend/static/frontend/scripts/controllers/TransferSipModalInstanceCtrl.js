export default class TransferSipModalInstanceCtrl {
  constructor(data, $uibModalInstance, EditMode, IP, $q) {
    const $ctrl = this;

    $ctrl.data = data;
    $ctrl.transferring = false;

    // Transfer IP
    $ctrl.transfer = function() {
      $ctrl.transferring = true;
      var promises = [];
      $ctrl.data.ips.forEach(function(ip) {
        promises.push(
          IP.transfer({
            id: ip.id,
            purpose: $ctrl.data.request.purpose,
          })
            .$promise.then(function(response) {
              $ctrl.transferring = false;
              return response;
            })
            .catch(function(response) {
              return response;
            })
        );
      });
      $q.all(promises).then(function(responses) {
        $ctrl.transferring = false;
        $uibModalInstance.close();
      });
    };

    $ctrl.cancel = function() {
      EditMode.disable();
      $uibModalInstance.dismiss('cancel');
    };
  }
}
