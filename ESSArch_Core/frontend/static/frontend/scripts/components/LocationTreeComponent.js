import LocationTreeCtrl from '../controllers/LocationTreeCtrl';

export default {
  templateUrl: 'static/frontend/views/location_tree.html',
  controller: ['$scope', '$http', 'appConfig', '$translate', '$uibModal', '$log', '$transitions', LocationTreeCtrl],
  controllerAs: 'vm',
  bindings: {
    selected: '=',
    onSelect: '&',
    readOnly: '<', // Disables context menu and hides related nodes
    hideTags: '<', // Hides tag list
  },
};
