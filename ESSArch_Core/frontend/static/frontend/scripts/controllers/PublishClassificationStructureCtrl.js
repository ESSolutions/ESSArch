export default class PublishClassificationStructureCtrl {
  constructor($http, appConfig, $uibModalInstance, data, $rootScope) {
    const $ctrl = this;
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
  }
}
