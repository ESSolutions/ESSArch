export default class PreviewConversionJobModalInstanceCtrl {
  constructor($translate, $uibModalInstance, appConfig, $http, data, $scope, listViewService, $uibModal) {
    const $ctrl = this;
    $ctrl.angular = angular;
    $ctrl.data = data;
    $ctrl.$onInit = () => {};

    $ctrl.displayedIps = [];
    $ctrl.callServer = function (tableState) {
      $ctrl.ipLoading = true;
      if ($ctrl.displayedIps.length == 0) {
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
          url: appConfig.djangoUrl + 'conversion-jobs/' + data.job.id + '/information-packages/',
          params: angular.extend(
            {
              search,
              ordering,
              view_type: 'flat',
              active: true,
              page: paginationParams.pageNumber,
              page_size: paginationParams.number,
              pager: paginationParams.pager,
              archived: true,
            },
            $ctrl.columnFilters
          ),
        })
          .then(function (response) {
            $ctrl.displayedIps = response.data;
            tableState.pagination.numberOfPages = Math.ceil(response.headers('Count') / paginationParams.number); //set the number of pages so the pagination can update
            $ctrl.ipLoading = false;
            $ctrl.initLoad = false;
          })
          .catch(function (response) {
            $ctrl.ipLoading = false;
            $ctrl.initLoad = false;
          });
      }
    };

    $ctrl.ok = function () {
      $uibModalInstance.close();
    };
    $ctrl.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };

    $ctrl.previewIpModal = function (job, ip) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/preview_ip_conversion_modal.html',
        controller: 'PreviewIpConversionModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'md',
        resolve: {
          data: {
            job,
            ip,
          },
        },
      });
      modalInstance.result.then(
        function (data) {},
        function () {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
  }
}
