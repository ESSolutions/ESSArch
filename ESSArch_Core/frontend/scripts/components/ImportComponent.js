angular.module('essarch.components').component('import', {
  templateUrl: 'import.html',
  controller: 'ImportCtrl',
  controllerAs: 'vm',
  bindings: {
    types: '<',
  },
});
