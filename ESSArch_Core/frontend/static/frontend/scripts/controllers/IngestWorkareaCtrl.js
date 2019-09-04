export default class IngestWorkareaCtrl {
  constructor($scope, $controller) {
    const vm = this;
    const ipSortString = [];
    vm.workarea = 'ingest';

    $controller('WorkareaCtrl', {$scope: $scope, vm: vm, ipSortString: ipSortString});
  }
}
