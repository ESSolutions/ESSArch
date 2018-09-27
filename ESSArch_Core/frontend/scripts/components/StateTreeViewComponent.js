angular.module('essarch.components').component('stateTreeView', {
    templateUrl: 'state_tree_view.html',
    controller: 'StateTreeCtrl',
    controllerAs: 'vm',
    bindings: {
        ip: '<'
    }
})
