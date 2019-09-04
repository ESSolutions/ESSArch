export default class AccessWorkareaCtrl {
  constructor($scope, $controller) {
    const vm = this;
    const ipSortString = [];
    vm.workarea = 'access';

    $controller('WorkareaCtrl', {$scope: $scope, vm: vm, ipSortString: ipSortString});
  }
}
