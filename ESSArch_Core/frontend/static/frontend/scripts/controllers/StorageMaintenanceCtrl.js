export default class StorageMaintenanceCtrl {
  constructor($scope, $rootScope) {
    const vm = this;
    $scope.select = true;
    vm.formFiltersShow = true;
    vm.needToMigrateShow = true;
    vm.migratePerPage = 10;
    vm.deactivatePerPage = 10;
    vm.migrationList = [];
    vm.deactivateList = [];
    vm.deactivateStorageMedium = true;
    vm.collapseNeedToMigrate = function() {
      vm.needToMigrateShow = !vm.needToMigrateShow;
    };

    vm.collapseFilters = function() {
      vm.formFiltersShow = !vm.formFiltersShow;
    };

    vm.collapseDeactivateStorageMedium = function() {
      vm.deactivateStorageMedium = !vm.deactivateStorageMedium;
    };

    vm.selectionList = [];

    vm.migration = {
      purpose: '',
      filters: {
        policyID: {
          value: '',
          options: ['Option 1', 'Option 2'],
        },
        currentMediumPrefix: {
          value: '',
          options: ['Option 1', 'Option 2'],
        },
        previousMediumPrefix: '',
        status: {
          value: '',
          options: ['Option 1', 'Option 2'],
        },
      },
    };
  }
}
