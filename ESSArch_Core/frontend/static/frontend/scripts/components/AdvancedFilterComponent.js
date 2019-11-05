import controller from '../controllers/AdvancedFilterCtrl';

export default {
  templateUrl: 'static/frontend/views/advanced_filters.html',
  controller: ['$scope', 'Filters', '$timeout', '$state', '$window', '$transitions', controller],
  controllerAs: 'vm',
  bindings: {
    activeModel: '=',
    fields: '<',
    type: '@', // Type of list (ip, event, medium)
    update: '&',
  },
};
