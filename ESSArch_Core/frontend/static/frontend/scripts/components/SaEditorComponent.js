import SaEditorCtrl from '../controllers/SaEditorCtrl';

export default {
  templateUrl: 'static/frontend/views/sa_editor.html',
  controller: [
    'Notifications',
    '$timeout',
    'SA',
    'Profile',
    '$scope',
    '$rootScope',
    '$http',
    'appConfig',
    '$anchorScroll',
    '$translate',
    SaEditorCtrl,
  ],
  controllerAs: 'vm',
  bindings: {},
};
