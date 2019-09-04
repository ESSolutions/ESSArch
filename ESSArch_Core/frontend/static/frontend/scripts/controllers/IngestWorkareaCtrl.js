export default class IngestWorkareaCtrl {
  constructor($scope, $controller) {
    var vm = this;
    var ipSortString = [];
    vm.workarea = 'ingest';

    $controller('WorkareaCtrl', {$scope: $scope, vm: vm, ipSortString: ipSortString});
  }
}
