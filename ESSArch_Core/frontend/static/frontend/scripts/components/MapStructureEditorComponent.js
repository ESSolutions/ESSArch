/**
 * Input profile is a profile
 * Input save is a function that sohuld have one argument which is the structure
 */

angular.module('essarch.components').component('mapStructureEditor', {
  templateUrl: 'static/frontend/views/map_structure_tree.html',
  controller: 'MapStructureEditorCtrl',
  controllerAs: 'vm',
  bindings: {
    profile: '<',
    save: '<',
  },
});
