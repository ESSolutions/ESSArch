import controller from '../controllers/ConversionSpecCtrl';

export default {
  templateUrl: 'static/frontend/views/conversion_spec.html',
  controller: ['$scope', '$http', '$translate', 'appConfig', '$uibModal', '$log', controller],
  controllerAs: 'vm',
  bindings: {
    specification: '=',
  },
};
