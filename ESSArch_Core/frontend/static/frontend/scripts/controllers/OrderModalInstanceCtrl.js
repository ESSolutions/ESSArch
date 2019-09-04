export default class OrderModalInstanceCtrl {
  constructor($uibModalInstance, data, $http, appConfig, listViewService) {
    const $ctrl = this;
    if (data) {
      $ctrl.data = data;
    }
    $ctrl.newOrder = function(label) {
      $ctrl.creatingOrder = true;
      listViewService
        .prepareOrder(label)
        .then(function(result) {
          $ctrl.creatingOrder = false;
          $uibModalInstance.close();
        })
        .catch(function(response) {
          $ctrl.creatingOrder = false;
        });
    };
    $ctrl.remove = function(order) {
      $ctrl.removing = true;
      $http({
        method: 'DELETE',
        url: appConfig.djangoUrl + 'orders/' + order.id + '/',
      })
        .then(function() {
          $ctrl.removing = false;
          $uibModalInstance.close();
        })
        .catch(function() {
          $ctrl.removing = false;
        });
    };
    $ctrl.ok = function() {
      $uibModalInstance.close();
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
