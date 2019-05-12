angular.module('essarch.controllers').controller('SearchAdminCtrl', function($scope, $rootScope, $state) {
  var vm = this;
  vm.$onInit = function() {
    if ($state.current.name === 'home.administration.searchAdmin') {
      $state.go('home.administration.searchAdmin.archiveManager');
    }
  };
  vm.activeTab = 0;
});
