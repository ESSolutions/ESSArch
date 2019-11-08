import ClassificationStructureEditorCtrl from '../controllers/ClassificationStructureEditorCtrl';

export default {
  templateUrl: 'static/frontend/views/classification_structure_editor.html',
  controller: [
    '$scope',
    '$http',
    'appConfig',
    'Notifications',
    '$uibModal',
    '$log',
    '$translate',
    'Structure',
    '$q',
    '$timeout',
    '$state',
    '$stateParams',
    '$rootScope',
    'myService',
    'listViewService',
    'StructureUnitRelation',
    '$transitions',
    ClassificationStructureEditorCtrl,
  ],
  controllerAs: 'vm',
  bindings: {},
};
