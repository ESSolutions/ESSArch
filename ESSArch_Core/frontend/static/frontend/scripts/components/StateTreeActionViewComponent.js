import StateTreeActionCtrl from '../controllers/StateTreeActionCtrl';

export default {
  templateUrl: 'static/frontend/views/state_tree_action_view.html',
  controller: [
    '$scope',
    '$translate',
    'Step',
    'Task',
    'appConfig',
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
    StateTreeActionCtrl,
  ],
  controllerAs: 'vm',
  bindings: {
    ip: '<',
  },
};
