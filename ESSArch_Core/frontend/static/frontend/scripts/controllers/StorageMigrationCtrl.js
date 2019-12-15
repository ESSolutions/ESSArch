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
    $uibModal
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
              view_type: $rootScope.auth.ip_list_view_type,
              page: paginationParams.pageNumber,
              page_size: paginationParams.number,
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
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          vm.resetFilters();
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
      modalInstance.result.then(
        function(data) {},
        function() {}
      );
    };
  }
}
