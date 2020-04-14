import {isEnabled} from './../features/utils';

export default class PreserveModalInstanceCtrl {
  constructor($uibModalInstance, data, Requests, $q, $controller, $scope, $rootScope) {
    const vm = this;
    $controller('TagsCtrl', {$scope: $scope, vm: vm});
    $scope.isEnabled = isEnabled;
    vm.angular = angular;
    vm.data = data;
    vm.requestTypes = data.types;
    vm.request = data.request;
    vm.preserving = false;

    vm.$onInit = function () {
      if (!vm.data.ips) {
        vm.data.ips = [vm.data.ip];
      }
    };

    vm.ok = function () {
      $uibModalInstance.close();
    };
    vm.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };

    // Preserve IP
    vm.preserve = function () {
      vm.preserving = true;
      let data = {
        purpose: vm.request.purpose,
      };

      const promises = [];
      vm.data.ips.forEach(function (ip) {
        promises.push(
          Requests.preserve(ip, data)
            .then(function (result) {
              return result;
            })
            .catch(function (response) {
              return response;
            })
        );
      });
      $q.all(promises).then(function (data) {
        $uibModalInstance.close(data);
        vm.preserving = false;
      });
    };
  }
}
