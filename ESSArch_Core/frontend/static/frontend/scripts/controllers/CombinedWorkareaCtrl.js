export default class {
  constructor($scope, $controller) {
    const vm = this;
    const ipSortString = [];
    vm.workarea = '';

    $controller('WorkareaCtrl', {$scope: $scope, vm: vm, ipSortString: ipSortString});
  }
}
