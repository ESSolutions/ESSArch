import Controller from '../controllers/MapStructureEditorCtrl';

/**
 * Input profile is a profile
 * Input save is a function that sohuld have one argument which is the structure
 */

export default {
  templateUrl: 'static/frontend/views/map_structure_tree.html',
  controller: ['$scope', '$rootScope', '$translate', Controller],
  controllerAs: 'vm',
  bindings: {
    profile: '<',
    save: '<',
  },
};
