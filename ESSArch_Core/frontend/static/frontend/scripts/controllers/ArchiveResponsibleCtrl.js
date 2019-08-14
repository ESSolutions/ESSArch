angular.module('essarch.controllers').controller('ArchiveResponsibleCtrl', function($timeout, $q, $uibModal, $log) {
  var vm = this;
  vm.responsibleLoading = false;
  vm.responsibleList = [];

  vm.$onInit = function() {
    vm.getResponsibleList().then(function(response) {
      vm.responsibleList = response.data;
    });
  };

  // Mocked data
  vm.getResponsibleList = function() {
    vm.responsibleLoading = true;
    var deferred = $q.defer();
    $timeout(function() {
      vm.responsibleLoading = false;
      deferred.resolve({
        data: [
          {name: 'Anders', id: '1'},
          {name: 'Berit', id: '2'},
          {name: 'Pelle', id: '3'},
          {name: 'Stina', id: '4'},
        ],
      });
    }, 600);
    return deferred.promise;
  };

  vm.createModal = function() {
    var modalInstance = $uibModal.open({
      animation: true,
      ariaLabelledBy: 'modal-title',
      ariaDescribedBy: 'modal-body',
      templateUrl: 'static/frontend/views/new_archive_responsible_modal.html',
      controller: 'ArchiveResponsibleModalInstanceCtrl',
      controllerAs: '$ctrl',
      size: 'lg',
      resolve: {
        data: function() {
          return {};
        },
      },
    });
    modalInstance.result.then(
      function(data) {},
      function() {
        $log.info('modal-component dismissed at: ' + new Date());
      }
    );
  };
});
