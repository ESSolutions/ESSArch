angular.module('essarch.components').component('eventTable', {
    templateUrl: 'event_table.html',
    controller: 'EventCtrl',
    controllerAs: 'vm',
    bindings: {
        ip: "<"
    }
  });
