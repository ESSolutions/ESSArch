import controller from '../controllers/ExportCtrl';

export default {
  templateUrl: 'static/frontend/views/export.html',
  controller: ['$scope', 'appConfig', '$http', '$window', 'SA', 'Profile', controller],
  controllerAs: 'vm',
  bindings: {},
};
