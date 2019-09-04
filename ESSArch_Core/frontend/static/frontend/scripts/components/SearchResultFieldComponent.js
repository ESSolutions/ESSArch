import Controller from '../controllers/SearchResultFieldCtrl';

export default {
  templateUrl: 'static/frontend/views/search_result_field.html',
  controller: Controller,
  controllerAs: 'vm',
  bindings: {
    label: '@',
    stronglabel: '<',
    data: '<',
    type: '@',
    break: '<',
  },
};
