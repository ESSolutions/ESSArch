import controller from '../controllers/ProfileCtrl';

export default {
  templateUrl: 'static/frontend/views/profile_editor.html',
  controller: [
    'SA',
    'IP',
    'Profile',
    'PermPermissionStore',
    'ProfileIp',
    'ProfileIpData',
    '$scope',
    'listViewService',
    '$log',
    '$uibModal',
    '$translate',
    '$filter',
    controller,
  ],
  controllerAs: 'vm',
  bindings: {
    ip: '<',
    sa: '<',
    shareData: '&',
    disabled: '<',
  },
};
