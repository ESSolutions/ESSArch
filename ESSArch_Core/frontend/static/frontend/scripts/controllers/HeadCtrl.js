export default class HeadCtrl {
  /*@ngInject*/
  constructor($scope, $rootScope, $translate, $state) {
    var vm = this;
    var appName = ' | ESSArch';
    vm.pageTitle = 'ESSArch';
    $scope.$on('$stateChangeSuccess', function(event, toState, toParams, fromState, fromParams) {
      vm.pageTitle =
        $translate.instant(
          toState.name
            .split('.')
            .pop()
            .toUpperCase()
        ) + appName;
    });
    $scope.$on('$translateChangeSuccess', function() {
      vm.pageTitle =
        $translate.instant(
          $state.current.name
            .split('.')
            .pop()
            .toUpperCase()
        ) + appName;
    });
    $rootScope.$on('UPDATE_TITLE', function(event, data) {
      vm.pageTitle = data.title + appName;
    });
  }
}
