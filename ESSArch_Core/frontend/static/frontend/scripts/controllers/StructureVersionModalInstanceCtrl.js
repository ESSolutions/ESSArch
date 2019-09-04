export default class StructureVersionModalInstanceCtrl {
  constructor($translate, $uibModalInstance, appConfig, $http, data, Notifications) {
    const $ctrl = this;
    $ctrl.data = {};
    $ctrl.fields = [];
    $ctrl.$onInit = function() {
      $ctrl.buildForm();
    };
    $ctrl.buildForm = function() {
      $ctrl.fields = [
        {
          key: 'version_name',
          type: 'input',
          templateOptions: {
            label: $translate.instant('VERSION'),
            required: true,
          },
        },
      ];
    };

    $ctrl.createNewVersion = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.creating = true;
      $http
        .post(appConfig.djangoUrl + 'structures/' + data.structure.id + '/new-version/', $ctrl.data)
        .then(function(response) {
          Notifications.add($translate.instant('ACCESS.NEW_VERSION_CREATED'), 'success');
          $ctrl.creating = false;
          $uibModalInstance.close(response.data);
        })
        .catch(function() {
          $ctrl.creating = false;
        });
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
