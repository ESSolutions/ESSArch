export default class StorageMigrationPreviewModalInstanceCtrl {
  constructor($uibModalInstance, data, $http, appConfig, $translate, listViewService, $scope) {
    const $ctrl = this;
    $ctrl.data = data;
    $ctrl.itemsPerPage = 10;
    $ctrl.previews = [];
    $ctrl.$onInit = () => {};

    $ctrl.expanded = [];

    $ctrl.updatePreviews = () => {
      $ctrl.previewPipe($ctrl.tableState);
    };

    $ctrl.previewPipe = tableState => {
      $ctrl.previewLoading = true;
      if ($ctrl.previews.length === 0) {
        $scope.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        $ctrl.tableState = tableState;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        let ordering = tableState.sort.predicate;
        if (tableState.sort.reverse) {
          ordering = '-' + ordering;
        }

        const paginationParams = listViewService.getPaginationParams(tableState.pagination, $ctrl.itemsPerPage);
        $http({
          method: 'GET',
          url: appConfig.djangoUrl + 'storage-migrations-preview/',
          params: {
            search,
            ordering,
            page: paginationParams.pageNumber,
            page_size: paginationParams.number,
            pager: paginationParams.pager,
            policy: data.policy,
            information_packages: data.information_packages,
            storage_methods: data.storage_methods,
          },
        })
          .then(function(response) {
            response.data.forEach(x => {
              if (!$ctrl.expanded.includes(x.id)) {
                x.collapsed = true;
                x.targets = [];
              } else {
                x.targets = [];
                x.targetsLoading = true;
                $ctrl
                  .getTargetsForIp(x)
                  .then(targets => {
                    x.targets = targets;
                    x.collapsed = false;
                    x.targetsLoading = false;
                  })
                  .catch(() => {
                    x.collapsed = true;
                    x.targetsLoading = false;
                  });
              }
            });
            $ctrl.previews = response.data;
            tableState.pagination.numberOfPages = Math.ceil(response.headers('Count') / paginationParams.number); //set the number of pages so the pagination can update
            $ctrl.previewLoading = false;
            $scope.initLoad = false;
          })
          .catch(function(response) {
            $ctrl.previewLoading = false;
          });
      }
    };

    $ctrl.togglePreviewRow = previewItem => {
      previewItem.targetsLoading = true;
      if (previewItem.collapsed) {
        $ctrl
          .getTargetsForIp(previewItem)
          .then(targets => {
            previewItem.targets = targets;
            previewItem.collapsed = false;
            $ctrl.expanded.push(previewItem.id);
            previewItem.targetsLoading = false;
          })
          .catch(() => {
            previewItem.targetsLoading = false;
          });
      } else {
        previewItem.collapsed = true;
        $ctrl.expanded.splice($ctrl.expanded.indexOf(previewItem.id), 1);
        previewItem.targetsLoading = false;
      }
    };

    $ctrl.getTargetsForIp = previewItem => {
      let params = {
        policy: data.policy,
        storage_methods: data.storage_methods,
      };
      return $http
        .get(appConfig.djangoUrl + 'storage-migrations-preview/' + previewItem.id + '/', {params})
        .then(response => {
          return response.data;
        });
    };

    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
