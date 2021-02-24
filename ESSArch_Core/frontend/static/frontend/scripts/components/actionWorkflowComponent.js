import ConversionCtrl from '../controllers/ActionWorkflowCtrl';

export default {
  templateUrl: 'static/frontend/views/actionworkflow.html',
  controller: ['$scope', '$rootScope', 'appConfig', '$translate', '$http', '$timeout', '$uibModal', ConversionCtrl],
  controllerAs: 'vm',
  bindings: {
    ip: '<',
    baseUrl: '@',
  },
};
