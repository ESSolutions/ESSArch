import controller from '../controllers/ImportCtrl';

export default {
  templateUrl: 'static/frontend/views/import.html',
  controller: [
    '$q',
    '$rootScope',
    '$scope',
    '$http',
    'IP',
    'Profile',
    'SA',
    'Notifications',
    '$uibModal',
    '$translate',
    'StoragePolicy',
    controller,
  ],
  controllerAs: 'vm',
  bindings: {
    types: '<',
  },
};
