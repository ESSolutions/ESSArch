angular.module('essarch.components').component('userDropdown', {
  templateUrl: 'user_dropdown.html',
  controller: 'UserDropdownCtrl',
  controllerAs: 'vm',
  bindings: {
    auth: '=',
  },
});
