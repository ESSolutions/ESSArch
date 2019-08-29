export default class AccessWorkareaCtrl {
  constructor($scope, $controller) {
    var vm = this;
    var ipSortString = [];
    vm.workarea = 'access';

    $controller('WorkareaCtrl', {$scope: $scope, vm: vm, ipSortString: ipSortString});
  }
}
