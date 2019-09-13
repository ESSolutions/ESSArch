export default class ReceiveModalInstanceCtrl {
  constructor($uibModalInstance, $scope, data, $translate, $uibModal, $log, $http, appConfig, $q, EditMode) {
    const vm = data.vm;
    $scope.saAlert = null;
    $scope.alerts = {
      receiveError: {type: 'danger', msg: $translate.instant('CANNOT_RECEIVE_ERROR')},
    };
    $scope.ip = data.ip;
    $scope.requestForm = true;
    $scope.approvedToReceive = false;
    $scope.profileEditor = true;
    $scope.receiveDisabled = false;
    $scope.$on('disable_receive', function() {
      $scope.receiveDisabled = true;
    });
    $scope.$on('update_ip', function(event, data) {
      const temp = angular.copy($scope.ip);
      $scope.ip = data.ip;
      vm.updateCheckedIp({id: temp.id}, $scope.ip);
    });
    EditMode.enable();

    $scope.getStoragePolicies().then(function(result) {
      vm.request.storagePolicy.options = result;
      if ($scope.ip.policy) {
        vm.request.storagePolicy.value = angular.copy($scope.ip.policy);
      } else if (vm.request.storagePolicy.options.length > 0) {
        vm.request.storagePolicy.value = angular.copy(vm.request.storagePolicy).options[0];
      }
      vm.request.informationClass = vm.request.storagePolicy.value
        ? vm.request.storagePolicy.value.information_class
        : null;
      $scope.getArchives().then(function(result) {
        vm.tags.archive.options = result;
        $scope.requestForm = true;
      });
    });
    vm.getProfileData = function($event) {
      vm.request.submissionAgreement.value = $event.submissionAgreement;
      if ($event.aipProfileId) {
        vm.request.profileData[$event.aipProfileId] = $event.aipModel;
      }
      if ($event.dipProfileId) {
        vm.request.profileData[$event.dipProfileId] = $event.dipModel;
      }
      if ($event.saObject) {
        vm.sa = $event.saObject;
      }
      if ($event.approved) {
        $scope.approvedToReceive = $event.approved;
      }
    };

    vm.fetchProfileData = function() {
      if ($scope.approvedToReceive) {
        $scope.approvedToReceive = false;
        $scope.$broadcast('get_profile_data', {});
      }
    };

    vm.confirmReceiveModal = function(ip) {
      let data = {
        ip: ip,
        validatorModal: vm.validatorModel,
        request: vm.request,
      };
      if (vm.tags.structureUnits.value) {
        data.structure_unit = vm.tags.structureUnits.value.id;
      }
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/confirm_receive_modal.html',
        controller: 'ConfirmReceiveCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: data,
        },
      });
      modalInstance.result
        .then(function(data) {
          vm.resetForm();
          EditMode.disable();
          $uibModalInstance.close(data);
        })
        .catch(function() {
          $log.info('modal-component dismissed at: ' + new Date());
        });
    };

    vm.skip = function() {
      vm.data = {
        status: 'skip',
      };
      EditMode.disable();
      $uibModalInstance.close(vm.data);
    };
    vm.cancel = function() {
      EditMode.disable();
      $uibModalInstance.dismiss('cancel');
    };
    $scope.$on('modal.closing', function(event, reason, closed) {
      if (
        (data.allow_close === null || angular.isUndefined(data.allow_close) || data.allow_close !== true) &&
        (reason === 'cancel' || reason === 'backdrop click' || reason === 'escape key press')
      ) {
        const message = $translate.instant('UNSAVED_DATA_WARNING');
        if (!confirm(message)) {
          event.preventDefault();
        } else {
          EditMode.disable();
        }
      }
    });
  }
}
