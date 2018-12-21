angular.module('essarch.components').component('sysInfoComponent', {
    templateUrl: 'sys_info_component.html',
    controller: 'SysInfoComponentCtrl',
    controllerAs: 'vm',
    bindings: {
        icon: '@',
        name: '@',
        version: '@'
    }
});
