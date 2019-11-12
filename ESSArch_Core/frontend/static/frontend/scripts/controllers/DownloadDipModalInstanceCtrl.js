export default class DownloadDipModalInstanceCtrl {
  constructor($uibModalInstance, data, appConfig, $window, $sce) {
    const $ctrl = this;
    if (data) {
      $ctrl.data = data;
    }
    $ctrl.order = {};

    $ctrl.fields = [];
    $ctrl.options = {
      type: [],
      consign_method: [],
    };
    $ctrl.$onInit = () => {
      if (data.ip) {
        $ctrl.ip = angular.copy(data.ip);
      }
    };

    $ctrl.download = () => {
      const showFile = $sce.trustAsResourceUrl(
        appConfig.djangoUrl + 'information-packages/' + data.ip.id + '/download-dip/'
      );
      $window.open(showFile, '_blank');
      $uibModalInstance.close();
    };

    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
