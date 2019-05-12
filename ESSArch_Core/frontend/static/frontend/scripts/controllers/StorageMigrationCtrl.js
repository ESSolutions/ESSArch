angular.module('essarch.controllers').controller('StorageMigrationCtrl', function($scope, $rootScope) {
  var vm = this;
  $scope.select = true;
  vm.formFiltersShow = true;
  vm.targetShow = true;
  vm.selectionListShow = true;
  vm.ipsPerPage = 10;
  vm.collapseTarget = function() {
    vm.targetShow = !vm.targetShow;
  };

  vm.collapseFilters = function() {
    vm.formFiltersShow = !vm.formFiltersShow;
  };

  vm.collapseSelectionList = function() {
    vm.selectionListShow = !vm.selectionListShow;
  };

  vm.selectionList = [];

  vm.migrationForm = {
    purpose: '',
    tempPath: '',
    copyPath: '',
    filters: {
      object: null,
      objectID: '',
      status: {
        value: '',
        options: ['Option 1', 'Option 2'],
      },
      currentMediumId: '',
      policyID: {
        value: '',
        options: ['Option 1', 'Option 2'],
      },
    },
    target: {
      mediumPrefix: false,
      prefixes: [{name: 'prefix 1', value: false}, {name: 'Prefix 2', value: false}],
      forceCopies: false,
    },
  };
});
