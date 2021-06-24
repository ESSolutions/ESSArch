//Component for SearchAidCtrl
import SearchAidCtrl from '../controllers/SearchAidCtrl';

export default {
  templateUrl: 'static/frontend/views/search_aid_view.html',
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
