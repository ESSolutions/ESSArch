import DeliveryCtrl from '../controllers/DeliveryCtrl';

export default {
  templateUrl: 'static/frontend/views/delivery.html',
  controller: [
    '$scope',
    'appConfig',
    '$http',
    '$timeout',
    '$uibModal',
    '$log',
    'listViewService',
    '$translate',
    'myService',
    '$state',
    '$stateParams',
    'AgentName',
    DeliveryCtrl,
  ],
  controllerAs: 'vm',
  bindings: {},
};
