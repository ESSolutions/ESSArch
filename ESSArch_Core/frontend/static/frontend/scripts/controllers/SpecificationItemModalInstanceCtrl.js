export default class SpecificationItemModalInstanceCtrl {
  constructor($translate, $uibModalInstance, data, $scope) {
    const $ctrl = this;
    $scope.angular = angular;
    $ctrl.data = data;
    $ctrl.specItem = null;
    $ctrl.$onInit = () => {
      $ctrl.specItem = angular.copy($ctrl.data.specItem);
      angular.extend($ctrl.specItem, $ctrl.data.specItem.options);
      delete $ctrl.specItem.options;
    };

    $ctrl.getKeyString = (key) => {
      if (key === 'tool') {
        return $translate.instant('ARCHIVE_MAINTENANCE.TOOL');
      } else if (key === 'path') {
        return $translate.instant('PATH');
      } else {
        return key;
      }
    };

    $ctrl.close = function () {
      $uibModalInstance.close();
    };
  }
}
