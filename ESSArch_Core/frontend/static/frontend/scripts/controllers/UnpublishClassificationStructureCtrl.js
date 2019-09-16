export default class UnpublishClassificationStructureCtrl {
  constructor($http, appConfig, $uibModalInstance, data, $rootScope) {
    const $ctrl = this;
    $ctrl.$onInit = function() {
      $ctrl.data = data;
    };
    $ctrl.unpublish = function() {
      $ctrl.unpublishing = true;
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'structures/' + data.structure.id + '/unpublish/',
        method: 'POST',
      })
        .then(function(response) {
          $ctrl.unpublishing = false;
          $uibModalInstance.close(response);
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.unpublishing = false;
        });
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
