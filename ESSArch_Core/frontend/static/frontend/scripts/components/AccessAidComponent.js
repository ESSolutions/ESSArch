import SearchAidCtrl from '../controllers/AccessAidCtrl';

export default {
  templateUrl: 'static/frontend/views/access_aid.html',
  controller: [
    '$uibModal',
    '$log',
    '$scope',
    '$http',
    'appConfig',
    '$state',
    '$stateParams',
    'AgentName',
    'myService',
    '$rootScope',
    '$translate',
    'listViewService',
    '$transitions',
    SearchAidCtrl,
  ],
  controllerAs: 'vm',
  bindings: {},
};
