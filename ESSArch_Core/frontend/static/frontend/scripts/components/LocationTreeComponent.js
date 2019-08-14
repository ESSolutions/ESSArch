angular.module('essarch.components').component('locationTree', {
  templateUrl: 'static/frontend/views/location_tree.html',
  controller: 'LocationTreeCtrl',
  controllerAs: 'vm',
  bindings: {
    selected: '=',
    onSelect: '&',
    readOnly: '<', // Disables context menu and hides related nodes
    hideTags: '<', // Hides tag list
  },
});
