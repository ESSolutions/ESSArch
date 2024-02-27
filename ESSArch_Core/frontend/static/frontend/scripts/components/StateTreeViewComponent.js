import StateTreeCtrl from '../controllers/StateTreeCtrl';

export default {
  templateUrl: 'static/frontend/views/state_tree_view.html',
  controller: [
    '$scope',
    '$translate',
    'Step',
    'Task',
    'appConfig',
    '$state',
    '$timeout',
    '$interval',
    'PermPermissionStore',
    '$q',
    '$uibModal',
    '$log',
    'StateTree',
    '$rootScope',
    '$transitions',
    'listViewService',
    StateTreeCtrl,
  ],
  controllerAs: 'vm',
  bindings: {
    ip: '<',
  },
};
