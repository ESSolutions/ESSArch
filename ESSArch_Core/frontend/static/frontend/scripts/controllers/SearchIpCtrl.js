angular
  .module('essarch.controllers')
  .controller('SearchIpCtrl', function(appConfig, $scope, $rootScope, $http, IP, $stateParams, Notifications, $state) {
    var vm = this;
    vm.$onInit = function() {
      vm.getIpObject($stateParams.id)
        .then(function(ip) {
          if (ip.archived) {
            vm.ip = ip;
            $rootScope.ip = ip;
            $rootScope.$broadcast('UPDATE_TITLE', {title: vm.ip.label});
          } else {
            Notifications.add('IP not found in archival storage', 'error');
            $state.go('home.access.search');
          }
        })
        .catch(function() {
          Notifications.add('IP not found in archival storage', 'error');
          $state.go('home.access.search');
        });
    };

    vm.getIpObject = function(id) {
      return $http.get(appConfig.djangoUrl + 'search/information_package/' + id + '/').then(function(response) {
        return IP.get({id: response.data._source.id}).$promise.then(function(resource) {
          return resource;
        });
      });
    };
  });
