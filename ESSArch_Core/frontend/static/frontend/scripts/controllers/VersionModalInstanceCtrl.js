export default class VersionModalInstanceCtrl {
  constructor(Search, $translate, $uibModalInstance, data, Notifications) {
    var $ctrl = this;
    $ctrl.node = data.node.original;

    $ctrl.createNewVersion = function(node) {
      Search.createNewVersion(node).then(function(response) {
        Notifications.add($translate.instant('ACCESS.NEW_VERSION_CREATED'), 'success');
        $uibModalInstance.close('added');
      });
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
