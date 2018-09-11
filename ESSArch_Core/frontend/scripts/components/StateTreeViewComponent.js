angular.module('myApp').component('stateTreeView', {
    templateUrl: 'state_tree_view.html',
    controller: 'StateTreeCtrl',
    controllerAs: 'vm',
    bindings: {
        ip: '<'
    }
})
