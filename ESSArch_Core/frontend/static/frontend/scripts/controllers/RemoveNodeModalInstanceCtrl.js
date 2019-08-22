export default class RemoveNodeModalInstanceCtrl {
  constructor(Search, $translate, $uibModalInstance, data, Notifications, $rootScope) {
    var $ctrl = this;
    $ctrl.data = data;
    $ctrl.node = data.node.original;

    $ctrl.removeNode = function() {
      $rootScope.skipErrorNotification = true;
      Search.removeNode($ctrl.node)
        .then(function(response) {
          Notifications.add($translate.instant('ACCESS.NODE_REMOVED'), 'success');
          $uibModalInstance.close('added');
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
        });
    };
    $ctrl.removeFromStructure = function() {
      $rootScope.skipErrorNotification = true;
      Search.removeNodeFromStructure($ctrl.node, $ctrl.data.structure.id)
        .then(function(response) {
          Notifications.add($translate.instant('ACCESS.NODE_REMOVED_FROM_STRUCTURE'), 'success');
          $uibModalInstance.close('removed');
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
        });
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
