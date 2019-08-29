export default class MoveToApprovalModalInstanceCtrl {
  constructor($uibModalInstance, data, Requests, $q) {
    var $ctrl = this;
    $ctrl.angular = angular;
    $ctrl.data = data;
    $ctrl.requestTypes = data.types;
    $ctrl.request = data.request;
    $ctrl.moving = false;

    $ctrl.$onInit = function() {
      if ($ctrl.data.ips == null) {
        $ctrl.data.ips = [$ctrl.data.ip];
      }
    };
    $ctrl.ok = function() {
      $uibModalInstance.close();
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };

    // Preserve IP
    $ctrl.moveToApproval = function() {
      $ctrl.moving = true;
      var data = {purpose: $ctrl.data.request.purpose};
      var promises = [];
      $ctrl.data.ips.forEach(function(ip) {
        promises.push(Requests.moveToApproval(ip, data).then(function(response) {}));
      });
      $q.all(promises).then(function(data) {
        $uibModalInstance.close(data);
        $ctrl.moving = false;
      });
    };
  }
}
