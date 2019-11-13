export default class StorageMigrationCtrl {
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
    $controller('BaseCtrl', {$scope: $scope, vm: vm, ipSortString: '', params: {}});
    vm.itemsPerPage = 10;
    $scope.job = null;
    $scope.jobs = [];
    vm.displayedJobs = [];
    vm.displayedMediums = [];
    vm.medium = null;
    vm.selectedMediums = [];
    vm.mediumsPerPage = 10;
    vm.mediumFilterModel = {};
    vm.mediumFilterFields = [];
    $scope.$on('REFRESH_LIST_VIEW', function(event, data) {
      if (vm.activePill === 'migrate') {
        vm.updateStorageMediums();
      }
      if (vm.medium) {
        vm.callServer($scope.tableState);
      }
      if (vm.activePill === 'tasks') {
        vm.updateJobsList();
      }
    });

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

        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.itemsPerPage);
        $http({
          method: 'GET',
          url: appConfig.djangoUrl + 'information-packages/',
          params: angular.extend(
            {
              search,
              ordering,
              view_type: 'flat',
              page: paginationParams.pageNumber,
              page_size: paginationParams.number,
              pager: paginationParams.pager,
              medium: vm.selectedMediums.length ? vm.selectedMediums.map(x => x.id) : null,
              migratable: true,
            },
            vm.columnFilters
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
                vm.columnFilters
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

    vm.jobsPipe = tableState => {
      $scope.jobsLoading = true;
      if (vm.displayedJobs.length === 0) {
        $scope.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        vm.jobsTableState = tableState;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        let ordering = tableState.sort.predicate;
        if (tableState.sort.reverse) {
          ordering = '-' + ordering;
        }

        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.jobsPerPage);
        $http({
          method: 'GET',
          url: appConfig.djangoUrl + 'storage-migrations/',
          params: {
            search,
            ordering,
            page: paginationParams.pageNumber,
            page_size: paginationParams.number,
            pager: paginationParams.pager,
          },
        })
          .then(function(response) {
            response.data.forEach(x => {
              x.flow_type = 'task';
            });
            vm.displayedJobs = response.data;
            tableState.pagination.numberOfPages = Math.ceil(response.headers('Count') / paginationParams.number); //set the number of pages so the pagination can update
            $scope.jobsLoading = false;
            $scope.initLoad = false;

            ipExists();
            SelectedIPUpdater.update(vm.displayedJobs, $scope.ips, $scope.ip);
          })
          .catch(function(response) {
            $scope.jobsLoading = false;
          });
      }
    };

    vm.updateJobsList = () => {
      vm.jobsPipe(vm.jobsTableState);
    };

    vm.migrationModal = function(ips) {
      if (ips.length <= 0) {
        if ($scope.ip !== null) {
          ips = [$scope.ip];
        }
      }
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/storage_migration_modal.html',
        controller: 'StorageMigrationModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return {
              ips: ips,
              policy: vm.mediumFilterModel.policy,
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $scope.getListViewData();
        },
        function() {}
      );
    };
    //Creates and shows modal with task information
    $scope.taskInfoModal = function(task) {
      const modalInstance = $uibModal.open({
        animation: true,
        size: 'lg',
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/modals/task_info_modal.html',
        controller: 'TaskInfoModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            currentStepTask: task,
          },
        },
      });
      modalInstance.result.then(function(data) {}, function() {});
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
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.mediumsPerPage);
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
              migratable: true,
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
      return (
        vm.selectedMediums.filter(x => {
          return x.id === medium.id;
        }).length > 0
      );
    };

    vm.selectMedium = (medium, event) => {
      if (vm.mediumSelected(medium)) {
        let removeIndex = null;
        vm.selectedMediums.forEach((x, idx) => {
          if (x.id === medium.id) {
            removeIndex = idx;
          }
        });
        if (removeIndex !== null) {
          vm.selectedMediums.splice(removeIndex, 1);
        } else {
        }
        if (vm.selectedMediums.length === 0) {
          $scope.ip = null;
          $scope.ips = [];
        } else {
          $scope.getListViewData();
        }
      } else {
        vm.selectedMediums.push(medium);
        $scope.getListViewData();
      }
    };

    vm.deselectAllMediums = () => {
      vm.selectedMediums = [];
    };

    vm.selectAllMediums = () => {
      vm.displayedMediums.forEach(x => {
        if (!vm.mediumSelected(x)) {
          vm.selectMedium(x);
        }
      });
      $scope.getListViewData();
    };
  }
}
