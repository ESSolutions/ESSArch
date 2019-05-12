angular
  .module('essarch.controllers')
  .controller('OrderModalInstanceCtrl', function(
    $uibModalInstance,
    data,
    $http,
    Notifications,
    appConfig,
    listViewService
  ) {
    var $ctrl = this;
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
      console.log(order);
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
  });
