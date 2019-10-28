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

    vm.$onInit = () => {
      vm.resetFilters();
      return $http.get(appConfig.djangoUrl + 'storage-policies/', {params: {pager: 'none'}}).then(response => {
        vm.options.policy = response.data;
        vm.buildFilters();
        return response.data;
      });
    };

    vm.buildFilters = () => {
      vm.filterFields = [
        {
          type: 'select',
          key: 'policy',
          templateOptions: {
            label: $translate.instant('STORAGE_POLICY'),
            options: vm.options.policy,
            labelProp: 'policy_name',
            valueProp: 'id',
          },
          defaultValue: vm.options.policy.length > 0 ? vm.options.policy[0].id : null,
        },
        {
          key: 'current_medium',
          type: 'input',
          templateOptions: {
            label: $translate.instant('CURRENTMEDIUMID'),
          },
        },
      ];
    };

    // IP List
    vm.callServer = function(tableState) {
      $scope.ipLoading = true;
      if (vm.displayedIps.length == 0) {
        $scope.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        $scope.tableState = tableState;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        let ordering = tableState.sort.predicate;
        if (tableState.sort.reverse) {
          ordering = '-' + ordering;
        }

        console.log('callserver storagemaintenance: ', angular.copy($scope.columnFilters));
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.itemsPerPage);
        $http({
          method: 'GET',
          url: appConfig.djangoUrl + 'information-packages/',
          params: angular.extend(
            {
              search,
              ordering,
              view_type: $rootScope.auth.ip_list_view_type,
              page: paginationParams.pageNumber,
              page_size: paginationParams.number,
              migratable: true,
            },
            $scope.columnFilters
          ),
        })
          .then(function(response) {
            vm.displayedIps = response.data;
            tableState.pagination.numberOfPages = Math.ceil(response.headers('Count') / paginationParams.number); //set the number of pages so the pagination can update
            $scope.ipLoading = false;
            $scope.initLoad = false;
            ipExists();
            SelectedIPUpdater.update(vm.displayedIps, $scope.ips, $scope.ip);
          })
          .catch(function(response) {
            if (response.status == 404) {
              const filters = angular.extend(
                {
                  state: ipSortString,
                },
                $scope.columnFilters
              );

              if (vm.workarea) {
                filters.workarea = vm.workarea;
              }

              listViewService.checkPages('ip', paginationParams.number, filters).then(function(response) {
                tableState.pagination.numberOfPages = response.numberOfPages; //set the number of pages so the pagination can update
                tableState.pagination.start =
                  response.numberOfPages * paginationParams.number - paginationParams.number;
                vm.callServer(tableState);
              });
            }
          });
      }
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
        StorageMedium.query({
          policy: $scope.columnFilters.policy,
          active: $scope.columnFilters.active,
          page: paginationParams.pageNumber,
          page_size: paginationParams.number,
          deactivatable: true,
          ordering,
          search,
        })
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
