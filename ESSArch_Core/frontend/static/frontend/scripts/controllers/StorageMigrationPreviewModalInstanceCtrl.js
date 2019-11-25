export default class StorageMigrationPreviewModalInstanceCtrl {
  constructor($uibModalInstance, data, $http, appConfig, $translate, $log, $scope) {
    const $ctrl = this;
    $ctrl.data = data;
    $ctrl.$onInit = () => {
      $ctrl.data.preview.forEach(x => {
        x.collapsed = true;
        x.targets = [];
      });
    };

    $ctrl.togglePreviewRow = previewItem => {
      previewItem.targetsLoading = true;
      if (previewItem.collapsed) {
        let sendData = {
          policy: data.policy,
          redundant: data.redundant,
          storage_methods: data.storage_methods,
        };
        $http
          .post(appConfig.djangoUrl + 'storage-migrations-preview/' + previewItem.id + '/', sendData)
          .then(response => {
            previewItem.targets = response.data;
            previewItem.collapsed = false;
            previewItem.targetsLoading = false;
          })
          .catch(() => {
            previewItem.targetsLoading = false;
          });
      } else {
        previewItem.collapsed = true;
        previewItem.targetsLoading = false;
      }
    };

    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
