angular
  .module('essarch.controllers')
  .controller('PublishClassificationStructureCtrl', function($http, appConfig, $uibModalInstance, data, $rootScope) {
    var $ctrl = this;
    $ctrl.$onInit = function() {
      $ctrl.data = data;
    };
    $ctrl.publish = function() {
      $ctrl.publishing = true;
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'structures/' + data.structure.id + '/publish/',
        method: 'POST',
      })
        .then(function(response) {
          $ctrl.publishing = false;
          $uibModalInstance.close(response);
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.publishing = false;
        });
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  });
