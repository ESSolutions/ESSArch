export default class ArchiveManagerCtrl {
  constructor($scope, $http, appConfig, $uibModal, $log, $state, $stateParams, myService) {
    var vm = this;
    $scope.$stateParams = $stateParams;
    vm.structure = null;
    vm.record = null;
    vm.archives = [];
    vm.fields = [];

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
        }
        var sorting = tableState.sort;
        var pagination = tableState.pagination;
        var start = pagination.start || 0; // This is NOT the page number, but the index of item in the list that you want to use to display the table.
        var number = pagination.number || vm.archivesPerPage; // Number of entries showed per page.
        var pageNumber = start / number + 1;

        var sortString = sorting.predicate;
        if (sorting.reverse) {
          sortString = '-' + sortString;
        }
        $http
          .get(appConfig.djangoUrl + 'tags/', {
            params: {
              index: 'archive',
              page: pageNumber,
              page_size: number,
              ordering: sortString,
              search: search,
            },
          })
          .then(function(response) {
            vm.archives = response.data;
            tableState.pagination.numberOfPages = Math.ceil(response.headers('Count') / number); //set the number of pages so the pagination can update
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
        $state.go('home.access.archiveManager');
      } else {
        vm.archiveLoading = true;
        vm.record = {_id: archive.current_version.id};
        $state.go('home.access.archiveManager.detail', {id: vm.record._id});
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
      var modalInstance = $uibModal.open({
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
          $state.go('home.access.archiveManager.detail', {id: data.archive._id});
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    vm.editArchiveModal = function(archive) {
      vm.getArchive(archive.current_version.id).then(function(result) {
        archive = result;
        var modalInstance = $uibModal.open({
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
            $state.go('home.access.archiveManager.detail', {id: archive._id}, {reload: true});
          },
          function() {
            $log.info('modal-component dismissed at: ' + new Date());
          }
        );
      });
    };
    vm.removeArchiveModal = function(archive) {
      var modalInstance = $uibModal.open({
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
          $state.go('home.access.archiveManager');
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
  }
}
