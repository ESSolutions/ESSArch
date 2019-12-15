export default class PreserveModalInstanceCtrl {
  constructor($uibModalInstance, data, Requests, $q, $controller, $scope) {
    const vm = this;
    $controller('TagsCtrl', {$scope: $scope, vm: vm});

    vm.angular = angular;
    vm.data = data;
    vm.requestTypes = data.types;
    vm.request = data.request;
    vm.preserving = false;

    vm.$onInit = function() {
      if (!vm.data.ips) {
        vm.data.ips = [vm.data.ip];
      }
      $scope.getArchives().then(function(result) {
        vm.tags.archive.options = result;
      });
    };

    $scope.updateTags = function() {
      $scope.tagsLoading = true;
      $scope.getArchives().then(result => {
        vm.tags.archive.options = result;
        $scope.requestForm = true;
        $scope.tagsLoading = false;
      });
    };

    vm.ok = function() {
      $uibModalInstance.close();
    };
    vm.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };

    // Preserve IP
    vm.preserve = function() {
      vm.preserving = true;
      let data = {
        purpose: vm.request.purpose,
        archive: vm.tags.archive.value ? vm.tags.archive.value.id : null,
        structure: vm.tags.structure.value ? vm.tags.structure.value.id : null,
      };
      if (vm.tags.structureUnits.value) {
        data.structure_unit = vm.tags.structureUnits.value.id;
      }
      const promises = [];
      vm.data.ips.forEach(function(ip) {
        promises.push(
          Requests.preserve(ip, data)
            .then(function(result) {
              return result;
            })
            .catch(function(response) {
              return response;
            })
        );
      });
      $q.all(promises).then(function(data) {
        $uibModalInstance.close(data);
        vm.preserving = false;
      });
    };
  }
}
