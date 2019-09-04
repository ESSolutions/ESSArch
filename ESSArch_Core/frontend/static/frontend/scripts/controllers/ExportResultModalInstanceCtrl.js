export default class ExportResultModalInstanceCtrl {
  constructor($uibModalInstance, data, $sce, $window) {
    const $ctrl = this;
    const vm = data.vm;
    $ctrl.formats = ['pdf', 'csv'];
    $ctrl.format = 'pdf';
    $ctrl.exporting = false;
    $ctrl.export = function() {
      const file = $sce.trustAsResourceUrl(vm.getExportResultUrl(vm.tableState, $ctrl.format));
      $window.open(file, '_blank');
      $uibModalInstance.close();
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
