export default class SavedSearchModalInstanceCtrl {
  constructor($uibModalInstance, appConfig, $http, data) {
    var $ctrl = this;
    $ctrl.$onInit = function() {
      $ctrl.data = data;
    };

    $ctrl.remove = function() {
      $http.delete(appConfig.djangoUrl + 'me/searches/' + $ctrl.data.search.id).then(function(response) {
        $uibModalInstance.close(response.data);
      });
    };
    $ctrl.save = function() {
      $ctrl.saving = true;
      $http
        .post(appConfig.djangoUrl + 'me/searches/', {name: $ctrl.name, query: $ctrl.data.filters})
        .then(function(response) {
          $ctrl.saving = false;
          $uibModalInstance.close(response.data);
        })
        .catch(function() {
          $ctrl.saving = false;
        });
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
