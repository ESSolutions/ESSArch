export default class ArchiveManagerCtrl {
  constructor(
    $scope,
    $http,
    appConfig,
    $uibModal,
    $log,
    $state,
    $stateParams,
    myService,
    listViewService,
    $translate,
    $transitions
  ) {
    const vm = this;
    $scope.$stateParams = $stateParams;
    $scope.$translate = $translate;
    vm.initialSearch = null;
    vm.structure = null;
    vm.record = null;
    vm.archives = [];
    vm.fields = [];

    vm.$onInit = () => {
      if ($stateParams.id) {
        vm.initialSearch = $stateParams.id;
      }
    };

    let watchers = [];
    watchers.push(
      $transitions.onSuccess({}, function($transition) {
        if ($transition.from().name !== $transition.to().name) {
          watchers.forEach(function(watcher) {
            watcher();
          });
        } else {
          let params = $transition.params();
          if (params.id !== null && (vm.record === null || params.id !== vm.record.id)) {
            vm.initialSearch = angular.copy($stateParams.id);
          } else if (params.id === null && vm.record !== null) {
            vm.archiveClick(vm.record);
          }
        }
      })
    );

    vm.getArchives = function(tableState) {
      vm.archivesLoading = true;
      if (vm.archives.length == 0) {
        $scope.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        $scope.tableState = tableState;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        } else {
          tableState.search = {
            predicateObject: {
              $: vm.initialSearch,
            },
          };
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        let sortString = sorting.predicate;
        if (sorting.reverse) {
          sortString = '-' + sortString;
        }
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.archivesPerPage);

        $http
          .get(appConfig.djangoUrl + 'tags/', {
            params: {
              index: 'archive',
              page: paginationParams.pageNumber,
              page_size: paginationParams.number,
              ordering: sortString,
              search: search,
            },
          })
          .then(function(response) {
            vm.archives = response.data;
            tableState.pagination.numberOfPages = Math.ceil(response.headers('Count') / paginationParams.number); //set the number of pages so the pagination can update
            tableState.pagination.totalItemCount = response.headers('Count');
            $scope.initLoad = false;
            vm.archivesLoading = false;
          });
      }
    };

    vm.updateArchives = function() {
      vm.getArchives($scope.tableState);
    };

    vm.getArchiveColspan = function() {
      if (myService.checkPermission('tags.change_archive') && myService.checkPermission('tags.delete_archive')) {
        return 5;
      } else if (
        myService.checkPermission('tags.change_archive') ||
        myService.checkPermission('tags.delete_archive')
      ) {
        return 4;
      } else {
        return 3;
      }
    };

    vm.archiveClick = function(archive) {
      if (vm.record !== null && archive.current_version.id === vm.record._id) {
        vm.record = null;
        $state.go('home.archivalDescriptions.archiveManager');
      } else {
        vm.archiveLoading = true;
        vm.record = {_id: archive.current_version.id};
        $state.go('home.archivalDescriptions.archiveManager.detail', {id: vm.record._id});
      }
    };

    vm.getArchive = function(id) {
      return $http.get(appConfig.djangoUrl + 'search/' + id + '/').then(function(response) {
        return response.data;
      });
    };

    vm.getTypes = function() {
      return $http
        .get(appConfig.djangoUrl + 'tag-version-types/', {params: {archive_type: true, pager: 'none'}})
        .then(function(response) {
          return angular.copy(response.data);
        });
    };

    vm.newArchiveModal = function() {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/new_archive_modal.html',
        controller: 'ArchiveModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: {},
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          vm.updateArchives();
          $state.go('home.archivalDescriptions.archiveManager.detail', {id: data.archive._id});
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    vm.editArchiveModal = function(archive) {
      vm.getArchive(archive.current_version.id).then(function(result) {
        archive = result;
        const modalInstance = $uibModal.open({
          animation: true,
          ariaLabelledBy: 'modal-title',
          ariaDescribedBy: 'modal-body',
          templateUrl: 'static/frontend/views/edit_archive_modal.html',
          controller: 'ArchiveModalInstanceCtrl',
          controllerAs: '$ctrl',
          size: 'lg',
          resolve: {
            data: {
              archive: archive,
            },
          },
        });
        modalInstance.result.then(
          function(data, $ctrl) {
            vm.updateArchives();
            $state.go('home.archivalDescriptions.archiveManager.detail', {id: archive._id}, {reload: true});
          },
          function() {
            $log.info('modal-component dismissed at: ' + new Date());
          }
        );
      });
    };
    vm.removeArchiveModal = function(archive) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_archive_modal.html',
        controller: 'ArchiveModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: {
            archive: archive,
            remove: true,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          vm.updateArchives();
          $state.go('home.archivalDescriptions.archiveManager');
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
  }
}
