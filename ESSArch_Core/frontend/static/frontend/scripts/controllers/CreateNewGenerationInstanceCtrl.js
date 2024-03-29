export default class CreateNewGenerationModalInstanceCtrl {
  constructor($uibModalInstance, data, Requests, $q) {
    const $ctrl = this;
    $ctrl.angular = angular;
    $ctrl.data = data;
    $ctrl.requestTypes = data.types;
    $ctrl.request = data.request;
    $ctrl.moving = false;

    $ctrl.$onInit = function () {
      if ($ctrl.data.ips == null) {
        $ctrl.data.ips = [$ctrl.data.ip];
      }
    };
    $ctrl.ok = function () {
      $uibModalInstance.close();
    };
    $ctrl.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };

    // createNewGeneration
    $ctrl.createNewGeneration = function () {
      $ctrl.moving = true;
      const data = {purpose: $ctrl.data.request.purpose};
      const promises = [];
      $ctrl.data.ips.forEach(function (ip) {
        promises.push(Requests.createNewGeneration(ip, data).then(function (response) {}));
      });
      $q.all(promises).then(function (data) {
        $uibModalInstance.close(data);
        $ctrl.moving = false;
      });
    };
  }
}
