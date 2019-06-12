import controller from '../controllers/FilebrowserController';

export default {
  templateUrl: 'static/frontend/views/filebrowser.html',
  controller: [
    '$scope',
    '$rootScope',
    '$sce',
    'appConfig',
    'listViewService',
    '$uibModal',
    '$window',
    '$cookies',
    '$state',
    controller,
  ],
  controllerAs: 'vm',
  bindings: {
    ip: '<',
    workarea: '<',
    user: '<',
    browserstate: '=',
  },
};
