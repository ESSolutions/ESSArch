angular.module('essarch.components').component('resultField', {
  templateUrl: 'static/frontend/views/search_result_field.html',
  controller: 'SearchResultFieldCtrl',
  controllerAs: 'vm',
  bindings: {
    label: '@',
    stronglabel: '<',
    data: '<',
    type: '@',
    break: '<',
  },
});
