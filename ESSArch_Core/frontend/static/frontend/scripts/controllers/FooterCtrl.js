angular.module('essarch.controllers').controller('FooterCtrl', function() {
  var vm = this;
  vm.$onInit = function() {
    vm.currentYear = new Date().getFullYear();
  };
});
