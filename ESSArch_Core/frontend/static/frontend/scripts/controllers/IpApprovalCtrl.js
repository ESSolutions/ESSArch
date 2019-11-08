export default class IpApprovalCtrl {
  constructor($scope, $controller, $rootScope, $translate, ContextMenuBase) {
    const vm = this;
    const ipSortString = ['Received', 'Preserving'];
    $controller('BaseCtrl', {$scope: $scope, vm: vm, ipSortString: ipSortString, params: {}});

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
      const methods = [];
      methods.push({
        text: $translate.instant('INFORMATION_PACKAGE_INFORMATION'),
        click: function() {
          vm.ipInformationModal(row);
        },
      });
      methods.push(
        ContextMenuBase.changeOrganization(function() {
          vm.changeOrganizationModal(row);
        })
      );
      return methods;
    };
  }
}
