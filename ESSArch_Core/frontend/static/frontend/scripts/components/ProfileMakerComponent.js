import Controller from '../controllers/ProfileMakerCtrl';

export default {
  templateUrl: 'static/frontend/views/profile_maker/index.html',
  controller: [
    'ProfileMakerTemplate',
    'ProfileMakerExtension',
    '$scope',
    '$state',
    '$http',
    '$uibModal',
    '$log',
    Controller,
  ],
  controllerAs: 'vm',
  bindings: {},
};
