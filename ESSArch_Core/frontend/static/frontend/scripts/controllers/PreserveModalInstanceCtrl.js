export default class PreserveModalInstanceCtrl {
  constructor($uibModalInstance, data, Requests, $q) {
    const $ctrl = this;
    $ctrl.angular = angular;
    $ctrl.data = data;
    $ctrl.requestTypes = data.types;
    $ctrl.request = data.request;
    $ctrl.preserving = false;

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
    $ctrl.preserve = function() {
      $ctrl.preserving = true;
      const params = {purpose: $ctrl.request.purpose};
      params.policy =
        $ctrl.request.storagePolicy && $ctrl.request.storagePolicy.value != ''
          ? $ctrl.request.storagePolicy.value.id
          : null;
      if ($ctrl.request.appraisal_date != null) {
        params.appraisal_date = $ctrl.request.appraisal_date;
      }
      const promises = [];
      $ctrl.data.ips.forEach(function(ip) {
        promises.push(
          Requests.preserve(ip, params)
            .then(function(result) {
              return result;
            })
            .catch(function(response) {
              return response;
            })
        );
      });
      $q.all(promises).then(function(data) {
        $uibModalInstance.close(data);
        $ctrl.preserving = false;
      });
    };
  }
}
