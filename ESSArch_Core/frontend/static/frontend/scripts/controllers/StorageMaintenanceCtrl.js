export default class StorageMaintenanceCtrl {
  constructor(
    $rootScope,
    $scope,
    appConfig,
    $http,
    listViewService,
    SelectedIPUpdater,
    $controller,
    $translate,
    $uibModal,
    StorageMedium
  ) {
    const vm = this;
    $scope.select = true;
    vm.formFiltersShow = true;
    vm.targetShow = true;
    vm.selectionListShow = true;
    vm.itemsPerPage = 10;
    $controller('BaseCtrl', {$scope: $scope, vm: vm, ipSortString: '', params: {}});
    vm.filters;
    $scope.job = null;
    $scope.jobs = [];
    vm.displayedJobs = [];
    vm.displayedMediums = [];
    vm.mediumFilterModel = {};
    vm.mediumFilterFields = [];

    $scope.$on('REFRESH_LIST_VIEW', function(event, data) {
      vm.updateStorageMediums();
    });

    vm.resetFilters = () => {
      vm.filters = {
        migratable: true,
      };
    };

    vm.options = {
      policy: [],
    };

    vm.filterFields = [];

    vm.initLoad = true;
    vm.$onInit = () => {
      return $http.get(appConfig.djangoUrl + 'storage-policies/', {params: {pager: 'none'}}).then(response => {
        if (response.data.length > 0) {
          vm.policyFilter = response.data[0];
          vm.mediumFilterModel.policy = response.data[0].id;
          vm.initLoad = false;
        }
        return response.data;
      });
    };

    // Medium List
    vm.updateStorageMediums = function() {
      vm.mediumPipe(vm.mediumTableState);
    };

    vm.mediumPipe = function(tableState) {
      $scope.mediumLoading = true;
      if (vm.displayedMediums.length == 0) {
        $scope.initMediumLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        vm.mediumTableState = tableState;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        let ordering = tableState.sort.predicate;
        if (tableState.sort.reverse) {
          ordering = '-' + ordering;
        }
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.itemsPerPage);
        if (
          (vm.mediumFilterModel.policy === null || angular.isUndefined(vm.mediumFilterModel.policy)) &&
          vm.policyFilter !== null
        ) {
          vm.mediumFilterModel.policy = vm.policyFilter.id;
          vm.mediumFilterFields.forEach(x => {
            if (x.key === 'policy') {
              x.addDefault(vm.policyFilter);
            }
          });
        }
        StorageMedium.query(
          angular.extend(
            {
              page: paginationParams.pageNumber,
              page_size: paginationParams.number,
              pager: paginationParams.pager,
              deactivatable: true,
              ordering,
              search,
            },
            vm.mediumFilterModel
          )
        )
          .$promise.then(function(resource) {
            vm.displayedMediums = resource;
            tableState.pagination.numberOfPages = Math.ceil(resource.$httpHeaders('Count') / paginationParams.number); //set the number of pages so the pagination can update
            $scope.mediumLoading = false;
            $scope.initMediumLoad = false;
            SelectedIPUpdater.update(vm.displayedMediums, [], $scope.storageMedium);
          })
          .catch(function(response) {
            if (response.status == 404) {
              const filters = {
                search: search,
              };

              listViewService.checkPages('storage_medium', paginationParams.number, filters).then(function(response) {
                tableState.pagination.numberOfPages = response.numberOfPages; //set the number of pages so the pagination can update
                tableState.pagination.start =
                  response.numberOfPages * paginationParams.number - paginationParams.number;
                vm.mediumPipe(tableState);
              });
            } else {
              $scope.mediumLoading = false;
            }
          });
      }
    };

    vm.mediumSelected = medium => {
      return vm.selectedMediums.some(x => x.id === medium.id);
    };

    vm.selectedMediums = [];
    vm.selectMedium = (medium, event) => {
      if (vm.mediumSelected(medium)) {
        vm.deselectMedium(medium);
      } else {
        vm.selectedMediums.push(medium);
      }
    };

    vm.deselectMedium = medium => {
      vm.selectedMediums.forEach((x, index, array) => {
        if (x.id === medium.id) {
          array.splice(index, 1);
        }
      });
    };

    vm.deactivateMediumModal = function(mediums) {
      const modalInstance = $uibModal.open({
        animation: true,
        size: 'lg',
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/deactivate_medium_modal.html',
        controller: 'DeactivateMediumModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            mediums,
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          vm.selectedMediums = [];
          vm.updateStorageMediums();
        },
        function() {}
      );
    };
  }
}
