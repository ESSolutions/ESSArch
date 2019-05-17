export default class {
  constructor($scope, $controller) {
    var vm = this;
    var ipSortString = [];
    vm.workarea = '';

    $controller('WorkareaCtrl', {$scope: $scope, vm: vm, ipSortString: ipSortString});
  }
}
