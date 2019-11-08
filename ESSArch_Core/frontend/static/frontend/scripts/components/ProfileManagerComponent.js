import Controller from '../controllers/ProfileManagerCtrl';

export default {
  templateUrl: 'static/frontend/views/profile_manager.html',
  controller: ['$state', '$scope', Controller],
  controllerAs: 'vm',
  bindings: {},
};
