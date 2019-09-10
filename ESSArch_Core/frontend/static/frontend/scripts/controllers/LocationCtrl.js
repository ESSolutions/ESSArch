export default class LocationCtrl {
  constructor($scope, $translate, $stateParams, $http, appConfig, $state) {
    const vm = this;
    $scope.$translate = $translate;
    vm.showTree = false;
    vm.location = null;
    vm.$onInit = function() {
      if ($stateParams.id) {
        $http.get(appConfig.djangoUrl + 'locations/' + $stateParams.id + '/').then(function(response) {
          vm.location = response.data;
          vm.showTree = true;
        });
      } else {
        vm.location = null;
        vm.showTree = true;
      }
    };

    vm.onSelect = function(node) {
      if (node.id !== $stateParams.id) {
        $state.go($state.current.name, {id: node.id});
      }
    };
  }
}
