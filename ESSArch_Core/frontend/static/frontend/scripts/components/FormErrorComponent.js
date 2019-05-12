angular.module('essarch.components').component('formErrors', {
  templateUrl: 'form_errors.html',
  controller: 'FormErrorsCtrl',
  controllerAs: 'vm',
  bindings: {
    errors: '=',
  },
});
