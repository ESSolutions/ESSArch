export default class StatsReportModalInstanceCtrl {
  constructor($uibModalInstance, appConfig, data, $sce, $window) {
    const $ctrl = this;
    $ctrl.selected = {};
    $ctrl.$onInit = function () {
      $ctrl.options = data.options;
    };

    $ctrl.generateReport = function () {
      const selected = [];
      angular.forEach($ctrl.selected, function (value, key) {
        if (value === true) {
          selected.push(key);
        }
      });
      const showFile = $sce.trustAsResourceUrl(appConfig.djangoUrl + 'stats/export/?fields=' + selected.join(','));
      $window.open(showFile, '_blank');
    };

    $ctrl.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
