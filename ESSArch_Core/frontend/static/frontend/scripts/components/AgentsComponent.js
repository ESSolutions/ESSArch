import AgentCtrl from '../controllers/AgentCtrl';

export default {
  templateUrl: 'static/frontend/views/agents.html',
  controller: [
    '$uibModal',
    '$log',
    '$scope',
    '$http',
    'appConfig',
    '$state',
    '$stateParams',
    ' AgentName',
    'myService',
    '$rootScope',
    '$translate',
    AgentCtrl,
  ],
  controllerAs: 'vm',
  bindings: {},
};
