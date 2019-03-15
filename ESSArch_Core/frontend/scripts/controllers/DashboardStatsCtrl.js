angular.module('essarch.controllers').controller('DashboardStatsCtrl', function($scope, appConfig, $http) {
  var vm = this;
  vm.$onInit = function() {
    vm.getStats().then(function(stats) {
      vm.stats = stats;
    });
  };

  vm.getStats = function() {
    return $http.get(appConfig.djangoUrl + 'stats/').then(function(response) {
      return response.data;
    });
  };
});
