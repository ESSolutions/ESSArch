angular.module('essarch.components').component('searchFilter', {
  templateUrl: 'static/frontend/views/search_filter.html',
  controller: 'SearchFilterCtrl',
  controllerAs: 'vm',
  bindings: {
    label: '@',
    options: '=', // Required
    update: '&', // Required
    labelProp: '@', // Required
    valueProp: '@', // Required
    ngModel: '=', // Required
    ngChange: '&',
    required: '<',
  },
});
