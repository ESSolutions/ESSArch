angular.module('essarch.controllers').controller('EditableFieldCtrl', function($scope) {
  var vm = this;
  $scope.angular = angular;
  vm.$onChanges = function() {
    if(angular.isUndefined(vm.inputClass)) {
      vm.inputClass = 'form-control';
    }
    if(angular.isUndefined(vm.textClass)) {
      vm.textClass = '';
    }
    if(angular.isUndefined(vm.type)) {
      vm.type = 'input';
    } else {
      vm.type = vm.type.toLowerCase();
    }
  }
})
