export default class PreviewIpAppraisalModalInstanceCtrl {
  constructor($translate, $uibModalInstance, appConfig, $http, data, $scope, listViewService) {
    const $ctrl = this;
    // Set later to use local time for next job
    $ctrl.angular = angular;
    $ctrl.data = data;
    $ctrl.$onInit = () => {};

    $ctrl.files = [];
    $ctrl.filePipe = function(tableState) {
      $ctrl.filesLoading = true;
      if ($ctrl.files.length == 0) {
        $ctrl.initLoad = true;
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
          url:
            appConfig.djangoUrl +
            'appraisal-jobs/' +
            data.job.id +
            '/information-packages/' +
            data.ip.id +
            '/preview/',
          params: {
            search,
            ordering,
            page: paginationParams.pageNumber,
            page_size: paginationParams.number,
            pager: paginationParams.pager,
          },
        })
          .then(function(response) {
            $ctrl.files = response.data;
            tableState.pagination.numberOfPages = Math.ceil(response.headers('Count') / paginationParams.number); //set the number of pages so the pagination can update
            $ctrl.filesLoading = false;
            $ctrl.initLoad = false;
          })
          .catch(function(response) {
            $ctrl.filesLoading = false;
            $ctrl.initLoad = false;
          });
      }
    };

    $ctrl.ok = function() {
      $uibModalInstance.close();
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
