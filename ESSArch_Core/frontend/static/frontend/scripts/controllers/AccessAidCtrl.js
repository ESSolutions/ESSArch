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
    $transitions
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

    let watchers = [];
    watchers.push(
      $transitions.onSuccess({}, function ($transition) {
        if ($transition.from().name !== $transition.to().name) {
          watchers.forEach(function (watcher) {
            watcher();
          });
        } else {
          let params = $transition.params();
          if (params.id !== null && (vm.accessAid === null || params.id !== vm.accessAid.id)) {
            vm.initialSearch = angular.copy($stateParams.id);
            vm.getAccessAid($stateParams).then(function () {
              $rootScope.$broadcast('UPDATE_TITLE', {title: vm.accessAid.name});
            });
          } else if (params.id === null && vm.accessAid !== null) {
            vm.agentClick(vm.accessAid);
          }
        }
      })
    );

    vm.getAgentListColspan = function () {
      if (myService.checkPermission('access.change_accessaid') && myService.checkPermission('access.delete_accessaid')) {
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

    vm.getAccessAid = function (agent) {
      return $http.get(appConfig.djangoUrl + 'access-aids/' + agent.id + '/').then(function (response) {
        vm.initAccordion();
        vm.accessAid = response.data;
        return response.data;
      });
    };

    vm.$onInit = function () {
      if ($stateParams.id) {
        vm.initialSearch = angular.copy($stateParams.id);
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

    vm.agentClick = function (agent) {
      if (vm.accessAid === null || (vm.accessAid !== null && agent.id !== vm.accessAid.id)) {
        $http.get(appConfig.djangoUrl + 'access-aids/' + agent.id + '/').then(function (response) {
          vm.accessAid = response.data;
          vm.initAccordion();
          vm.accessAid = agent;
          $state.go($state.current.name, vm.accessAid);
          $rootScope.$broadcast('UPDATE_TITLE', {title: vm.accessAid.name});
        });
      } else if (vm.accessAid !== null && vm.accessAid.id === agent.id) {
        vm.accessAid = null;
        $state.go($state.current.name, {id: null});
        $translate.instant($state.current.name.split('.').pop().toUpperCase());
        $rootScope.$broadcast('UPDATE_TITLE', {
          title: $translate.instant($state.current.name.split('.').pop().toUpperCase()),
        });
      }
    };

    vm.sortNames = function (agent) {
      agent.names.sort(function (a, b) {
        return new Date(b.start_date) - new Date(a.start_date);
      });
      const authorized = [];
      agent.names.forEach(function (x, index) {
        if (x.authority) {
          const name = x;
          agent.names.splice(index, 1);
          authorized.unshift(name);
        }
      });
      authorized.forEach(function (x) {
        agent.names.unshift(x);
      });
    };

    vm.archiveClick = function (agentArchive) {
      $state.go('home.archivalDescriptions.search.archive', {id: agentArchive.archive._id});
    };

    vm.accessAidPipe = function (tableState) {
      vm.accessAidsLoading = true;
      if (vm.accessAids.length == 0) {
        $scope.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        $scope.tableState = tableState;
        var search = '';
        if (tableState.search.predicateObject) {
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

        vm.getAgents({
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

    vm.getAgents = function (params) {
      return $http({
        url: appConfig.djangoUrl + 'access-aids/',
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
    vm.removeAgentModal = function (accessAid) {
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
