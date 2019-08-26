import SearchFilterCtrl from '../controllers/SearchFilterCtrl';

export default {
  templateUrl: 'static/frontend/views/search_filter.html',
  controller: ['$scope', '$window', '$rootScope', SearchFilterCtrl],
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
};
