import StateTreeCtrl from '../controllers/StateTreeCtrl';

export default {
  templateUrl: 'static/frontend/views/state_tree_view.html',
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
    StateTreeCtrl,
  ],
  controllerAs: 'vm',
  bindings: {
    ip: '<',
  },
};
