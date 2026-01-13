export default class AccessAidCtrl {
  constructor(
    $uibModal,
    $log,
    $scope,
    $http,
    appConfig,
    $state,
    $stateParams,
    AgentName,
    myService,
    $rootScope,
    $translate,
    listViewService,
    $transitions,
    $timeout
  ) {
    const vm = this;
    $scope.AgentName = AgentName;
    $scope.$state = $state;
    $scope.$translate = $translate;
    vm.initialSearch = null;
    vm.accessAidsLoading = false;
    vm.accessAids = [];
    vm.accessAid = null;
    vm.accordion = {
      basic: {
        basic: {
          open: true,
        },
        related_structure_units: {
          open: true,
        },
      },
    };
    vm.urlSelect = false;

    vm.value = 1;
    vm.addOne = () => {
      //$ctrl.value = $ctrl.value + 1;
      //console.log('added one', $ctrl.value);
      //$scope.$apply();
      vm.value = vm.value + 1;
      console.log('bla', vm.value);
    };

    let watchers = [];
    watchers.push(
      $transitions.onSuccess({}, function ($transition) {
        if ($transition.from().name !== $transition.to().name) {
          watchers.forEach(function (watcher) {
            watcher();
          });
        } else {
          let params = $transition.params();
          console.log('$transitions.onSuccess - AccessAidCtrl - params:', params);
          const fromRowClick = sessionStorage.getItem('accessAidFromRowClick') === 'true';
          if (params.id && !fromRowClick) {
            console.log('$transitions.onSuccess - AccessAidCtrl - set vm.initialSearch:', params.id);
            vm.initialSearch = params.id;
            vm.searchTerm = params.id;
            console.log('vm.accessAid:', vm.accessAid);
            vm.urlSelect = true;
            vm.getAccessAid({id: params.id}).then(() => {
              console.log('AccessAid loaded:', vm.accessAid);

              // Update table if tableState exists
              if ($scope.tableState) {
                console.log('$transitions.onSuccess - AccessAidCtrl - vm.accessAidPipe');
                // force the search to the new ID from URL
                $scope.tableState.search = $scope.tableState.search || {};
                $scope.tableState.search.predicateObject = {$: vm.initialSearch};
                vm.accessAidPipe($scope.tableState);
              } else {
                console.log('$transitions.onSuccess - AccessAidCtrl - no tableState');
                vm.accessAidPipe(undefined); // fallback if no tableState
              }

              // Now safe to call accessAidClick
              console.log('$transitions.onSuccess - AccessAidCtrl - accessAidClick');
              vm.accessAidClick(vm.accessAid, {fromUrl: true});
            });
          } else {
            sessionStorage.removeItem('accessAidFromRowClick');
          }
        }
      })
    );

    vm.getAccessAidListColspan = function () {
      if (
        myService.checkPermission('access.change_accessaid') &&
        myService.checkPermission('access.delete_accessaid')
      ) {
        return 6;
      } else if (
        myService.checkPermission('access.change_accessaid') ||
        myService.checkPermission('access.delete_accessaid')
      ) {
        return 5;
      } else {
        return 4;
      }
    };

    vm.getAccessAid = function (accessAid) {
      return $http.get(appConfig.djangoUrl + 'access-aids/' + accessAid.id + '/').then(function (response) {
        vm.initAccordion();
        vm.accessAid = response.data;
        return response.data;
      });
    };

    vm.$onInit = function () {
      if ($stateParams.id) {
        vm.initialSearch = angular.copy($stateParams.id);
        vm.urlSelect = true;
        vm.getAccessAid($stateParams).then(function () {
          $rootScope.$broadcast('UPDATE_TITLE', {title: vm.accessAid.name});
        });
      } else {
        vm.accessAid = null;
      }
    };

    vm.initAccordion = function () {
      angular.forEach(vm.accordion, function (value) {
        value.open = true;
      });
    };

    vm.accessAidClick = function (accessAid, options = {}) {
      console.log('AccessAid clicked:', accessAid, 'vm.urlSelect:', vm.urlSelect, 'vm.accessAid:', vm.accessAid);
      const isUserClick = !options.fromUrl;
      if (vm.accessAid === null || (vm.accessAid !== null && accessAid.id !== vm.accessAid.id)) {
        $http.get(appConfig.djangoUrl + 'access-aids/' + accessAid.id + '/').then(function (response) {
          vm.accessAid = response.data;
          vm.initAccordion();
          // Only trigger the table pipe **once**, after data is ready
          $timeout(() => {
            vm.accessAid.structureUnits = response.data.structureUnits || [];
            if ($scope.structureUnitTableState) {
              vm.accessAidStructureUnitPipe($scope.structureUnitTableState);
            }
          });
          $state.go($state.current.name, vm.accessAid).then(() => {
            $rootScope.$broadcast('UPDATE_TITLE', {
              title: vm.accessAid.name,
            });
          });
          if (!vm.urlSelect) {
            // Mark that URL change came from UI
            sessionStorage.setItem('accessAidFromRowClick', 'true');
          }
        });
      } else if (vm.accessAid !== null && vm.accessAid.id === accessAid.id && isUserClick) {
        vm.accessAid = null;
        if (vm.urlSelect) {
          $scope.clearSearch();
        }
        vm.urlSelect = false;
        // Reset tableState so Smart Table won't trigger
        if ($scope.structureUnitTableState) {
          delete $scope.structureUnitTableState;
        }
        $state.go($state.current.name, {id: null});
        $translate.instant($state.current.name.split('.').pop().toUpperCase());
        $rootScope.$broadcast('UPDATE_TITLE', {
          title: $translate.instant($state.current.name.split('.').pop().toUpperCase()),
        });
      }
    };

    $scope.clearSearch = function () {
      console.log('Clearing search');
      vm.searchTerm = '';
      vm.initialSearch = '';
      delete $scope.tableState.search.predicateObject;
      vm.accessAidPipe($scope.tableState);
    };

    vm.accessAidPipe = function (tableState) {
      vm.accessAidsLoading = true;
      if (vm.accessAids.length == 0) {
        $scope.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        $scope.tableState = tableState;
        var search = '';
        if (tableState.search.predicateObject && tableState.search.predicateObject['$']) {
          search = tableState.search.predicateObject['$'];
        } else {
          tableState.search = {
            predicateObject: {
              $: vm.initialSearch,
            },
          };
          search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.itemsPerPage);

        let sortString = sorting.predicate;
        if (sorting.reverse) {
          sortString = '-' + sortString;
        }

        vm.getAccessAids({
          page: paginationParams.pageNumber,
          page_size: paginationParams.number,
          pager: paginationParams.pager,
          ordering: sortString,
          search: search,
        }).then(function (response) {
          tableState.pagination.numberOfPages = Math.ceil(response.headers('Count') / paginationParams.number); //set the number of pages so the pagination can update
          $scope.initLoad = false;
          vm.accessAidsLoading = false;
          vm.accessAids = response.data;
        });
      }
    };

    vm.getAccessAids = function (params) {
      return $http({
        url: appConfig.djangoUrl + 'access-aids/',
        method: 'GET',
        params: params,
      }).then(function (response) {
        return response;
      });
    };

    vm.accessAidStructureUnitPipe = function (tableState) {
      vm.structureUnitsLoading = true;
      if (angular.isUndefined(vm.accessAid.structureUnits) || vm.accessAid.structureUnits.length == 0) {
        $scope.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        $scope.structureUnitTableState = tableState;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.accessAidsPerPage);

        let sortString = sorting.predicate;
        if (sorting.reverse) {
          sortString = '-' + sortString;
        }

        vm.getAccessAidStructureUnit(vm.accessAid, {
          page: paginationParams.pageNumber,
          page_size: paginationParams.number,
          pager: paginationParams.pager,
          ordering: sortString,
          search: search,
        }).then(function (response) {
          tableState.pagination.numberOfPages = Math.ceil(response.headers('Count') / paginationParams.number); //set the number of pages so the pagination can update
          $scope.initLoad = false;
          vm.structureUnitsLoading = false;
          vm.accessAid.structureUnits = response.data;
        });
      }
    };

    vm.getAccessAidStructureUnit = function (accessAid, params) {
      return $http({
        url: appConfig.djangoUrl + 'access-aids/' + accessAid.id + '/structure-units/',
        method: 'GET',
        params: params,
      }).then(function (response) {
        return response;
      });
    };

    vm.createModal = function () {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/new_access_aid_modal.html',
        controller: 'AccessAidModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function () {
            return {};
          },
        },
      });
      modalInstance.result.then(
        function (data) {
          vm.accessAidPipe($scope.tableState);
          $state.go($state.current.name, {id: data.id});
        },
        function () {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.editModal = function (accessAid) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/edit_access_aid_modal.html',
        controller: 'AccessAidModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function () {
            return {
              accessAid: accessAid,
            };
          },
        },
      });
      modalInstance.result.then(
        function (data) {
          vm.accessAidPipe($scope.tableState);
          if (vm.accessAid) {
            vm.getAccessAid(vm.accessAid);
          }
        },
        function () {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    vm.removeAccessAidModal = function (accessAid) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_access_aid_modal.html',
        controller: 'AccessAidModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function () {
            return {
              accessAid: accessAid,
              allow_close: true,
              remove: true,
            };
          },
        },
      });
      modalInstance.result.then(
        function (data) {
          vm.accessAid = null;
          $state.go($state.current.name, {id: null});
          $rootScope.$broadcast('UPDATE_TITLE', {
            title: $translate.instant($state.current.name.split('.').pop().toUpperCase()),
          });
          vm.accessAidPipe($scope.tableState);
        },
        function () {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
  }
}
