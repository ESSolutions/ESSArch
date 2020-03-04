import controller from '../controllers/ConversionSpecCtrl';

export default {
  templateUrl: 'static/frontend/views/conversion_spec.html',
  controller: ['$http', '$translate', 'appConfig', controller],
  controllerAs: 'vm',
  bindings: {
    specification: '=',
  },
};
