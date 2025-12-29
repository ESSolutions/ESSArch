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
    ContextMenuBase,
    $transitions,
    ArchiveState
  ) {
    const vm = this;
    $scope.$stateParams = $stateParams;
    $scope.$translate = $translate;
    vm.initialSearch = null;
    vm.structure = null;
    vm.record = null;
    vm.archives = [];
    vm.fields = [];
    vm.urlSelect = false;
    $scope.ArchiveManagerInit = false;

    vm.$onInit = () => {
      const id = $stateParams.id;
      const fromRowClick = sessionStorage.getItem('archiveIdFromRowClick') === 'true';
      console.log('vm.$onInit - ArchiveManagerCtrl - id:', id, 'fromRowClick:', fromRowClick);
      if (id && !fromRowClick) {
        console.log('vm.$onInit - ArchiveManagerCtrl - set vm.initialSearch:', id);
        vm.initialSearch = id;
        vm.urlSelect = true;
        vm.record = {_id: id};
      } else if (id && fromRowClick) {
        $state.go('home.archivalDescriptions.archiveManager');
      }
      $scope.ArchiveManagerInit = true;
    };

    $scope.$watch(
      () => ArchiveState.getSelectedId(),
      (id) => {
        console.log('got new getSelectedId:', id);
        vm.record = {_id: id};
        const fromRowClick = sessionStorage.getItem('archiveIdFromRowClick') === 'true';
        if (id && !fromRowClick) {
          vm.initialSearch = id;
          vm.searchTerm = id;
          vm.urlSelect = true;
          if ($scope.tableState) {
            vm.getArchives($scope.tableState);
          }
        }
      }
    );

    $scope.menuOptions = function (rowType, row) {
      const methods = [];
      if (myService.checkPermission('tags.change_organization')) {
        methods.push(
          ContextMenuBase.changeOrganization(function () {
            vm.changeOrganizationModal(rowType, row);
          })
        );
      }
      return methods;
    };

    vm.changeOrganizationModal = function (itemType, item) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/modals/change_organization_modal.html',
        controller: 'OrganizationModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'md',
        resolve: {
          data: function () {
            return {
              itemType: itemType,
              item: item,
            };
          },
        },
      });
      modalInstance.result
        .then(function (data) {
          vm.updateArchives();
        })
        .catch(function () {
          $log.info('modal-component dismissed at: ' + new Date());
        });
    };

    let watchers = [];
    watchers.push(
      $transitions.onSuccess({}, function ($transition) {
        if ($transition.from().name !== $transition.to().name) {
          watchers.forEach(function (watcher) {
            watcher();
          });
        }

        let params = $transition.params();
        console.log('$transitions.onSuccess - ArchiveManagerCtrl - params:', params);
        const fromRowClick = sessionStorage.getItem('archiveIdFromRowClick') === 'true';
        if (params.id && !fromRowClick) {
          console.log('$transitions.onSuccess - ArchiveManagerCtrl - set vm.initialSearch:', params.id);
          vm.initialSearch = params.id;
          vm.searchTerm = params.id;
          vm.record = {_id: params.id};
          vm.urlSelect = true;
          if ($scope.tableState) {
            vm.getArchives($scope.tableState);
          }
        }

        if ($scope.ArchiveManagerInit) {
          console.log(
            '$transitions.onSuccess - ArchiveManagerCtrl - remove archiveIdFromRowClick and set AMinit to false'
          );
          sessionStorage.removeItem('archiveIdFromRowClick');
          $scope.ArchiveManagerInit = false;
        }
      })
    );

    vm.getArchives = function (tableState) {
      console.log('vm.getArchives');
      vm.archivesLoading = true;
      if (vm.archives.length == 0) {
        $scope.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        $scope.tableState = tableState;
        var search = '';
        if (tableState.search.predicateObject && tableState.search.predicateObject['$']) {
          var search = tableState.search.predicateObject['$'];
        } else {
          tableState.search = {
            predicateObject: {
              $: vm.initialSearch,
            },
          };
          var search = tableState.search.predicateObject['$'];
        }
        console.log('vm.getArchives - search:', search);
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
              pager: paginationParams.pager,
              ordering: sortString,
              search: search,
            },
          })
          .then(function (response) {
            vm.archives = response.data;
            console.log('vm.getArchives then - vm.archives:', vm.archives);
            tableState.pagination.numberOfPages = Math.ceil(response.headers('Count') / paginationParams.number); //set the number of pages so the pagination can update
            $scope.initLoad = false;
            vm.archivesLoading = false;
          });
      }
    };

    vm.updateArchives = function () {
      vm.getArchives($scope.tableState);
    };

    vm.getArchiveColspan = function () {
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

    vm.archiveClick = function (archive) {
      console.log(
        'vm.archiveClick - vm.record:',
        vm.record,
        'archive.current_version.id:',
        archive.current_version.id,
        'vm.urlSelect:',
        vm.urlSelect
      );
      if (vm.record !== null && archive.current_version.id === vm.record._id) {
        vm.record = null;
        ArchiveState.setSelectedId(null);
        $state.go('home.archivalDescriptions.archiveManager');
        if (vm.urlSelect) {
          $scope.clearSearch();
        }
        vm.urlSelect = false;
      } else {
        vm.archiveLoading = true;
        vm.record = {_id: archive.current_version.id};
        if (!vm.urlSelect) {
          // Mark that URL change came from UI
          sessionStorage.setItem('archiveIdFromRowClick', 'true');
        }
        $state.go('home.archivalDescriptions.archiveManager.detail', {id: vm.record._id});
      }
    };

    $scope.clearSearch = function () {
      console.log('Clearing search');
      vm.searchTerm = '';
      vm.initialSearch = '';
      delete $scope.tableState.search.predicateObject;
      vm.updateArchives();
    };

    vm.searchClick = function (archive) {
      console.log('vm.searchClick archive.current_version.id:', archive.current_version.id);
      vm.archiveLoading = true;
      vm.record = {_id: archive.current_version.id};
      $state.go('home.archivalDescriptions.search.component', {id: vm.record._id});
    };

    vm.getArchive = function (id) {
      console.log('vm.getArchive id:', id);
      return $http.get(appConfig.djangoUrl + 'search/' + id + '/').then(function (response) {
        return response.data;
      });
    };

    vm.getTypes = function () {
      return $http
        .get(appConfig.djangoUrl + 'tag-version-types/', {params: {archive_type: true, pager: 'none'}})
        .then(function (response) {
          return angular.copy(response.data);
        });
    };

    vm.newArchiveModal = function () {
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
        function (data, $ctrl) {
          vm.updateArchives();
          $state.go('home.archivalDescriptions.archiveManager.detail', {id: data.archive._id});
        },
        function () {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    vm.editArchiveModal = function (archive) {
      console.log('vm.editArchiveModal archive.current_version.id:', archive.current_version.id);
      vm.getArchive(archive.current_version.id).then(function (result) {
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
          function (data, $ctrl) {
            vm.updateArchives();
            $state.go('home.archivalDescriptions.archiveManager.detail', {id: archive._id}, {reload: true});
          },
          function () {
            $log.info('modal-component dismissed at: ' + new Date());
          }
        );
      });
    };
    vm.removeArchiveModal = function (archive) {
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
        function (data, $ctrl) {
          vm.updateArchives();
          $state.go('home.archivalDescriptions.archiveManager');
        },
        function () {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
  }
}
