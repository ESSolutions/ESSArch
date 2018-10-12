angular.module('essarch.components').component('essarchFooter', {
    templateUrl: 'footer.html',
    controller: 'FooterCtrl',
    controllerAs: 'vm',
    bindings: {
        title: '@'
    }
  });
