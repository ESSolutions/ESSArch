import ConversionCtrl from '../controllers/ConversionCtrl';

export default {
  templateUrl: 'static/frontend/views/conversion_view.html',
  controller: [
    '$scope',
    '$rootScope',
    'appConfig',
    '$translate',
    '$http',
    '$timeout',
    '$uibModal',
    'Notifications',
    '$cacheFactory',
    '$log',
    ConversionCtrl,
  ],
  controllerAs: 'vm',
  bindings: {
    ip: '<',
    baseUrl: '@',
  },
};
