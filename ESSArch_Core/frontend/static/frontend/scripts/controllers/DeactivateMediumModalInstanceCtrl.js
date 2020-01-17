export default class DeacivateMediumModalInstanceCtrl {
  constructor($uibModalInstance, appConfig, $http, $scope, data, $q) {
    const $ctrl = this;
    $ctrl.deactivating = false;

    $ctrl.mediums = angular.copy(data.mediums);
    $ctrl.deactivate = () => {
      $ctrl.deactivating = true;
      let promises = [];
      data.mediums.forEach(medium => {
        promises.push(
          $http({
            url: appConfig.djangoUrl + 'storage-mediums/' + medium.id + '/deactivate/',
            method: 'POST',
          })
        );
      });

      $q.all(promises)
        .then(response => {
          $ctrl.deactivating = false;
          $uibModalInstance.close(response);
        })
        .catch(response => {
          $ctrl.deactivating = false;
        });
    };

    $ctrl.cancel = () => {
      $uibModalInstance.dismiss();
    };
  }
}
