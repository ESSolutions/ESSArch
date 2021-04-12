export default class DataModalInstanceCtrl {
  constructor(IP, $scope, $sce, $uibModalInstance, Notifications, data, $q, $uibModal) {
    const $ctrl = this;
    if (data.vm) {
      var vm = data.vm;
    }
    $scope.prepareAlert = null;
    $ctrl.data = data;

    $scope.trustAsHtml = function (string) {
      return $sce.trustAsHtml(string);
    };

    $ctrl.$onInit = function () {
      if ($ctrl.data.ips == null) {
        $ctrl.data.ips = [$ctrl.data.ip];
      }
    };

    // Show fullscreen validation message
    $ctrl.showFullscreenMessage = function () {
      $ctrl.fullscreenActive = true;
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/validation_fullscreen_message.html',
        controller: 'DataModalInstanceCtrl',
        controllerAs: '$ctrl',
        windowClass: 'fullscreen-modal',
        resolve: {
          data: {
            validation: $ctrl.data.validation,
          },
        },
      });
      modalInstance.result.then(
        function (data) {
          $ctrl.fullscreenActive = false;
        },
        function () {
          $ctrl.fullscreenActive = false;
          $console.log('modal-component dismissed at: ' + new Date());
        }
      );
    };
    $ctrl.ok = function () {
      $uibModalInstance.close();
    };

    // Close prepare alert
    $scope.closePrepareAlert = function () {
      $scope.prepareAlert = null;
    };

    // Prepare IP for upload
    $ctrl.prepareForUpload = function () {
      $ctrl.preparing = true;
      const promises = [];
      $ctrl.data.ips.forEach(function (ip) {
        promises.push(
          IP.prepareForUpload({id: ip.id})
            .$promise.then(function (resource) {
              $ctrl.preparing = false;
              $uibModalInstance.close();
            })
            .catch(function (response) {
              return response;
            })
        );
      });
      $q.all(promises).then(function (responses) {
        $ctrl.preparing = false;
        $uibModalInstance.close();
      });
    };

    // Set IP as uploaded
    $ctrl.setUploaded = function () {
      $ctrl.settingUploaded = true;
      const promises = [];
      $ctrl.data.ips.forEach(function (ip) {
        promises.push(
          IP.setUploaded({
            id: ip.id,
          })
            .$promise.then(function (response) {
              $ctrl.settingUploaded = false;
              $uibModalInstance.close();
            })
            .catch(function (response) {
              if (response.status !== 404) {
                return response;
              }
            })
        );
      });
      $q.all(promises).then(function (responses) {
        $ctrl.settingUploaded = false;
        $uibModalInstance.close();
      });
    };

    // Create SIP from IP
    $ctrl.createSip = function () {
      $ctrl.creating = true;
      const promises = [];
      $ctrl.data.ips.forEach(function (ip) {
        promises.push(
          IP.create({
            id: ip.id,
            validators: vm.validatorModel,
            file_conversion: vm.fileConversionModel.file_conversion,
          })
            .$promise.then(function (response) {
              $ctrl.creating = false;
              $uibModalInstance.close();
            })
            .catch(function (response) {
              if (response.status == 404) {
                Notifications.add('IP could not be found', 'error');
              } else {
                return response;
              }
            })
        );
      });
      $q.all(promises).then(function (responses) {
        $ctrl.creating = false;
        $uibModalInstance.close();
      });
    };

    // Submit SIP
    $ctrl.submit = function () {
      $ctrl.submitting = true;
      const promises = [];
      $ctrl.data.ips.forEach(function (ip) {
        promises.push(
          IP.submit(angular.extend({id: ip.id}, {validators: vm.validatorModel}))
            .$promise.then(function (response) {
              $ctrl.submitting = false;
              $uibModalInstance.close();
            })
            .catch(function (response) {
              return response;
            })
        );
      });
      $q.all(promises).then(function (responses) {
        $ctrl.submitting = false;
        $uibModalInstance.close();
      });
    };

    // Remove IP
    $ctrl.remove = function (ipObject) {
      $ctrl.removing = true;
      IP.delete({
        id: ipObject.id,
      })
        .$promise.then(function () {
          $ctrl.removing = false;
          $uibModalInstance.close($ctrl.data);
        })
        .catch(function (response) {
          $ctrl.removing = false;
        });
    };

    $ctrl.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
