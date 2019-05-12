angular
  .module('essarch.controllers')
  .controller('IpApprovalCtrl', function(
    $scope,
    $controller,
    $rootScope,
    Resource,
    $interval,
    $timeout,
    appConfig,
    $cookies,
    $anchorScroll,
    $translate,
    listViewService,
    $http,
    $q,
    $state,
    Requests,
    ContextMenuBase
  ) {
    var vm = this;
    var ipSortString = ['Received', 'Preserving'];
    $controller('BaseCtrl', {$scope: $scope, vm: vm, ipSortString: ipSortString});

    //Request form data
    $scope.initRequestData = function() {
      vm.request = {
        type: '',
        purpose: '',
        storageMedium: {
          value: '',
          options: ['Disk', 'Tape(type1)', 'Tape(type2)'],
        },
        appraisal_date: null,
      };
    };
    $scope.initRequestData();

    $scope.menuOptions = function(rowType, row) {
      var methods = [];
      methods.push({
        text: $translate.instant('INFORMATION_PACKAGE_INFORMATION'),
        click: function($itemScope, $event, modelValue, text, $li) {
          $scope.ip = row;
          $rootScope.ip = row;
          vm.ipInformationModal($scope.ip);
        },
      });
      methods.push(
        ContextMenuBase.changeOrganization(function() {
          $scope.ip = row;
          $rootScope.ip = row;
          vm.changeOrganizationModal($scope.ip);
        })
      );
      return methods;
    };
  });
