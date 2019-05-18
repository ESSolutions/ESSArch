export default class DataModalInstanceCtrl {
  constructor(IP, $scope, $uibModalInstance, Notifications, data, $q) {
    var $ctrl = this;
    if (data.vm) {
      var vm = data.vm;
    }
    $ctrl.email = {
      subject: '',
      body: '',
    };
    $scope.prepareAlert = null;
    $ctrl.data = data;

    $ctrl.$onInit = function() {
      if ($ctrl.data.ips == null) {
        $ctrl.data.ips = [$ctrl.data.ip];
      }
    };

    // Close prepare alert
    $scope.closePrepareAlert = function() {
      $scope.prepareAlert = null;
    };

    // Prepare IP for upload
    $ctrl.prepareForUpload = function() {
      $ctrl.preparing = true;
      var promises = [];
      $ctrl.data.ips.forEach(function(ip) {
        promises.push(
          IP.prepareForUpload({id: ip.id})
            .$promise.then(function(resource) {
              $ctrl.preparing = false;
              $uibModalInstance.close();
            })
            .catch(function(response) {
              return response;
            })
        );
      });
      $q.all(promises).then(function(responses) {
        $ctrl.preparing = false;
        $uibModalInstance.close();
      });
    };

    // Set IP as uploaded
    $ctrl.setUploaded = function() {
      $ctrl.settingUploaded = true;
      var promises = [];
      $ctrl.data.ips.forEach(function(ip) {
        promises.push(
          IP.setUploaded({
            id: ip.id,
          })
            .$promise.then(function(response) {
              $ctrl.settingUploaded = false;
              $uibModalInstance.close();
            })
            .catch(function(response) {
              if (response.status !== 404) {
                return response;
              }
            })
        );
      });
      $q.all(promises).then(function(responses) {
        $ctrl.settingUploaded = false;
        $uibModalInstance.close();
      });
    };

    // Create SIP from IP
    $ctrl.createSip = function() {
      $ctrl.creating = true;
      var promises = [];
      $ctrl.data.ips.forEach(function(ip) {
        promises.push(
          IP.create({
            id: ip.id,
            validators: vm.validatorModel,
            file_conversion: vm.fileConversionModel.file_conversion,
          })
            .$promise.then(function(response) {
              $ctrl.creating = false;
              $uibModalInstance.close();
            })
            .catch(function(response) {
              if (response.status == 404) {
                Notifications.add('IP could not be found', 'error');
              } else {
                return response;
              }
            })
        );
      });
      $q.all(promises).then(function(responses) {
        $ctrl.creating = false;
        $uibModalInstance.close();
      });
    };

    // Submit SIP
    $ctrl.submit = function(email) {
      if (!email) {
        var sendData = {validators: vm.validatorModel};
      } else {
        var sendData = {validators: vm.validatorModel, subject: email.subject, body: email.body};
      }
      $ctrl.submitting = true;
      var promises = [];
      $ctrl.data.ips.forEach(function(ip) {
        promises.push(
          IP.submit(angular.extend({id: ip.id}, sendData))
            .$promise.then(function(response) {
              $ctrl.submitting = false;
              $uibModalInstance.close();
            })
            .catch(function(response) {
              return response;
            })
        );
      });
      $q.all(promises).then(function(responses) {
        $ctrl.submitting = false;
        $uibModalInstance.close();
      });
    };

    // Remove IP
    $ctrl.remove = function(ipObject) {
      $ctrl.removing = true;
      IP.delete({
        id: ipObject.id,
      })
        .$promise.then(function() {
          $ctrl.removing = false;
          $uibModalInstance.close($ctrl.data);
        })
        .catch(function(response) {
          $ctrl.removing = false;
        });
    };

    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
