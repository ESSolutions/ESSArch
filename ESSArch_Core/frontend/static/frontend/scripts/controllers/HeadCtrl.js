export default class HeadCtrl {
  /*@ngInject*/
  constructor($scope, $rootScope, $translate, $state, $transitions) {
    const vm = this;
    const appName = ' | ESSArch';
    vm.pageTitle = 'ESSArch';
    $transitions.onSuccess({}, function($transition) {
      vm.pageTitle =
        $translate.instant(
          $transition
            .$to()
            .name.split('.')
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
