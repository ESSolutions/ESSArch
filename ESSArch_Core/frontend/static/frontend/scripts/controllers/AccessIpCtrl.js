export default class AccessIpCtrl {
  constructor($scope, $controller, $rootScope, $translate, $uibModal, $log, ContextMenuBase, $transitions) {
    const vm = this;
    const ipSortString = ['Preserved'];
    $controller('BaseCtrl', {$scope: $scope, vm: vm, ipSortString: ipSortString, params: {}});
    vm.archived = true;

    $scope.ips = [];

    $scope.menuOptions = function(rowType, row) {
      const methods = [];
      methods.push({
        text: $translate.instant('APPRAISAL'),
        click: function($itemScope, $event, modelValue, text, $li) {
          if ($scope.ips.length === 0) {
            $scope.ip = row;
            $rootScope.ip = row;
            vm.openAppraisalModal($scope.ips);
          } else {
            vm.openAppraisalModal($scope.ips);
          }
        },
      });
      methods.push({
        text: $translate.instant('CONVERSION'),
        click: function($itemScope, $event, modelValue, text, $li) {
          if ($scope.ips.length === 0) {
            $scope.ip = row;
            $rootScope.ip = row;
            vm.openConversionModal($scope.ips);
          } else {
            vm.openConversionModal($scope.ips);
          }
        },
      });
      methods.push(
        ContextMenuBase.changeOrganization(function() {
          $scope.ip = row;
          $rootScope.ip = row;
          vm.changeOrganizationModal($scope.ip);
        })
      );

      methods.push({
        text: $translate.instant('INFORMATION_PACKAGE_INFORMATION'),
        click: function($itemScope, $event, modelValue, text, $li) {
          $scope.ip = row;
          $rootScope.ip = row;
          vm.ipInformationModal($scope.ip);
        },
      });
      return methods;
    };

    const watchers = [];
    watchers.push(
      $scope.$watch(
        function() {
          return $scope.ip;
        },
        function(newVal, oldVal) {
          if (newVal != null) {
            $scope.ips = [];
          }
        }
      )
    );

    //Destroy watchers on state change
    $transitions.onSuccess({}, function($transition) {
      if ($transition.from().name !== $transition.to().name) {
        watchers.forEach(function(watcher) {
          watcher();
        });
      }
    });

    $scope.selectedAmongOthers = function(id) {
      let exists = false;
      $scope.ips.forEach(function(ip) {
        if (ip.id == id) {
          exists = true;
        }
      });
      return exists;
    };

    $scope.clickSubmit = function() {
      $scope.submitRequest($scope.ips, vm.request);
    };

    // Requests
    $scope.submitRequest = function(ips, request) {
      switch (request.type) {
        case 'get':
        case 'get_tar':
        case 'get_as_new':
          if ($scope.ips.length) {
            vm.accessModal($scope.ips, request);
          } else if ($scope.ip != null) {
            vm.accessModal($scope.ip, request);
          }
          break;
        default:
          console.log('request not matched');
          break;
      }
    };

    vm.openAppraisalModal = function(ips) {
      if (ips.length == 0 && $scope.ip != null) {
        ips.push($scope.ip);
      }
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/appraisal_modal.html',
        controller: 'AppraisalModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return {
              ips: ips,
            };
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

    vm.openConversionModal = function(ips) {
      if (ips.length == 0 && $scope.ip != null) {
        ips.push($scope.ip);
      }
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/conversion_modal.html',
        controller: 'ConversionModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return {
              ips: ips,
            };
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
    vm.ipInformationModal = function(ip) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/ip_information_modal.html',
        controller: 'IpInformationModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return {
              ip: ip,
            };
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
  }
}
