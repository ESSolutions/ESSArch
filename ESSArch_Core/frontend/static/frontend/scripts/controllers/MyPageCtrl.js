export default class MyPageCtrl {
  constructor(Notifications, $scope, $controller, $rootScope) {
    var vm = this;
    $scope.visibleRequests = {
      access: false,
      workarea: false,
      receive: false,
    };
    $scope.tableControlCollapsed = true;
    $controller('BaseCtrl', {$scope: $scope, vm: vm, ipSortString: 'Preserving,Receiving'});
    vm.displayedIps = [
      {
        label: 'request',
        responsible: {username: 'admin'},
        create_date: new Date(),
        RequestType: 'Request type',
      },
    ];
  }
}
