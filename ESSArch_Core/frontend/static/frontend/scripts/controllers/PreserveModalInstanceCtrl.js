angular
  .module('essarch.controllers')
  .controller('PreserveModalInstanceCtrl', function($uibModalInstance, data, $scope, Requests, $q) {
    var $ctrl = this;
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
      var params = {purpose: $ctrl.request.purpose};
      params.policy =
        $ctrl.request.archivePolicy && $ctrl.request.archivePolicy.value != ''
          ? $ctrl.request.archivePolicy.value.id
          : null;
      if ($ctrl.request.appraisal_date != null) {
        params.appraisal_date = $ctrl.request.appraisal_date;
      }
      var promises = [];
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
  });
