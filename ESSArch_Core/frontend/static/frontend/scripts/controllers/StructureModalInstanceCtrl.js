angular
  .module('essarch.controllers')
  .controller('StructureModalInstanceCtrl', function(
    Search,
    $translate,
    $uibModalInstance,
    djangoAuth,
    appConfig,
    $http,
    data,
    $scope,
    Notifications,
    $timeout
  ) {
    var $ctrl = this;
    $ctrl.node = data.node;
    $ctrl.creating = false;

    $ctrl.createNewStructure = function(node) {
      $ctrl.creating = true;
      Search.createNewStructure(node, {name: $ctrl.structureName})
        .then(function(response) {
          Notifications.add($translate.instant('ACCESS.NEW_STRUCTURE_CREATED'), 'success');
          $uibModalInstance.close('added');
          $ctrl.creating = false;
        })
        .catch(function(response) {
          $ctrl.creating = false;
          Notifications.add('Error creating new structure', 'error');
        });
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  });
