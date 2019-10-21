import controller from '../controllers/LocationCtrl';

export default {
  templateUrl: 'static/frontend/views/location.html',
  controller: ['$scope', '$translate', '$stateParams', '$http', 'appConfig', '$state', controller],
  controllerAs: 'vm',
  bindings: {},
};
