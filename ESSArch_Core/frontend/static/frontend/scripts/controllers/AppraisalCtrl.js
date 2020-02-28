export default class AppraisalCtrl {
  constructor(
    $scope,
    appConfig,
    $http,
    $uibModal,
    $log,
    $sce,
    $window,
    Notifications,
    $interval,
    Appraisal,
    $translate,
    $transitions,
    listViewService
  ) {
    const vm = this;
    vm.templatesPerPage = 10;
    vm.ongoingPerPage = 10;
    vm.nextPerPage = 10;
    vm.finishedPerPage = 10;
    $scope.templateLoading = false;
    $scope.ongoingLoading = false;
    $scope.nextLoading = false;
    $scope.finishedLoading = false;

    $scope.$translate = $translate;

    //Cancel update intervals on state change
    $transitions.onSuccess({}, function($transition) {
      $interval.cancel(appraisalInterval);
    });

    $scope.$on('REFRESH_LIST_VIEW', function(event, data) {
      vm.nextPipe(vm.nextTableState);
      vm.ongoingPipe(vm.ongoingTableState);
      vm.finishedPipe(vm.finishedTableState);
    });

    var appraisalInterval = $interval(function() {
      vm.templatePipe(vm.templateTableState);
      vm.nextPipe(vm.nextTableState);
      vm.ongoingPipe(vm.ongoingTableState);
      vm.finishedPipe(vm.finishedTableState);
    }, appConfig.ipInterval);

    $scope.$on('REFRESH_LIST_VIEW', function(event, data) {
      vm.templatePipe(vm.templateTableState);
      vm.nextPipe(vm.nextTableState);
      vm.ongoingPipe(vm.ongoingTableState);
      vm.finishedPipe(vm.finishedTableState);
    });

    /**
     * Smart table pipe function for appraisal templates
     * @param {*} tableState
     */
    vm.templatePipe = function(tableState) {
      $scope.templateLoading = true;
      if (!angular.isUndefined(tableState)) {
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        let sortString = sorting.predicate;
        if (sorting.reverse) {
          sortString = '-' + sortString;
        }
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.templatesPerPage);
        Appraisal.getTemplates(paginationParams, sortString, search).then(function(response) {
          tableState.pagination.numberOfPages = Math.ceil(response.count / paginationParams.number); //set the number of pages so the pagination can update
          tableState.pagination.totalItemCount = response.count;
          vm.templateTableState = tableState;
          vm.templateFilters.forEach(function(x) {
            response.data.forEach(function(template) {
              if (x == template.id) {
                template.usedAsFilter = true;
              }
            });
          });
          vm.templates = response.data;
          $scope.templateLoading = false;
        });
      }
    };

    /**
     * Smart table pipe function for ongoing appraisals
     * @param {*} tableState
     */
    vm.ongoingPipe = function(tableState) {
      $scope.ongoingLoading = true;
      if (!angular.isUndefined(tableState)) {
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        let sortString = sorting.predicate;
        if (sorting.reverse) {
          sortString = '-' + sortString;
        }
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.ongoingPerPage);
        Appraisal.getOngoing(paginationParams, sortString, search).then(function(response) {
          tableState.pagination.numberOfPages = Math.ceil(response.count / paginationParams.number); //set the number of pages so the pagination can update
          tableState.pagination.totalItemCount = response.count;
          vm.ongoingTableState = tableState;
          vm.ongoing = response.data;
          $scope.ongoingLoading = false;
        });
      }
    };

    /**
     * Smart table pipe function for next appraisals
     * @param {*} tableState
     */
    vm.nextPipe = function(tableState) {
      $scope.nextLoading = true;
      if (!angular.isUndefined(tableState)) {
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        let sortString = sorting.predicate;
        if (sorting.reverse) {
          sortString = '-' + sortString;
        }
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.nextPerPage);
        Appraisal.getNext(paginationParams, sortString, search).then(function(response) {
          tableState.pagination.numberOfPages = Math.ceil(response.count / paginationParams.number); //set the number of pages so the pagination can update
          tableState.pagination.totalItemCount = response.count;
          vm.nextTableState = tableState;
          vm.next = response.data;
          $scope.nextLoading = false;
        });
      }
    };

    /**
     * Smart table pipe function for finished appraisals
     * @param {*} tableState
     */
    vm.finishedPipe = function(tableState) {
      $scope.finishedLoading = true;
      if (!angular.isUndefined(tableState)) {
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        let sortString = sorting.predicate;
        if (sorting.reverse) {
          sortString = '-' + sortString;
        }
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.finishedPerPage);
        Appraisal.getFinished(paginationParams, sortString, search).then(function(response) {
          tableState.pagination.numberOfPages = Math.ceil(response.count / paginationParams.number); //set the number of pages so the pagination can update
          tableState.pagination.totalItemCount = response.count;
          vm.finishedTableState = tableState;
          vm.finished = response.data;
          $scope.finishedLoading = false;
        });
      }
    };

    /*
     * Array containing chosen(checked) appraisal templates to use
     * as filter for the other appraisal tables
     */
    vm.templateFilters = [];

    /**
     * Add chosen appraisal template to list of filters or remove it.
     * Connected to apprailsal template table checkbox
     * @param {Object} template
     */
    vm.useAsFilter = function(template) {
      if (!vm.templateFilters.includes(template.id)) {
        template.used_as_filter = true;
        vm.templateFilters.push(template.id);
      } else {
        vm.templateFilters.splice(vm.templateFilters.indexOf(template.id), 1);
        template.used_as_filter = false;
      }
    };
    /**
     * Show appraisal report
     * @param {Object} appraisal
     */
    vm.showReport = function(appraisal) {
      const file = $sce.trustAsResourceUrl(appConfig.djangoUrl + 'appraisal-jobs/' + appraisal.id + '/report/');
      $window.open(file, '_blank');
    };

    /**
     *  Clear search input
     */
    $scope.clearSearch = function() {
      delete vm.templateTableState.search.predicateObject;
      $('#search-input')[0].value = '';
      vm.templatePipe();
    };
    /**
     * MODALS
     */

    vm.runJobModal = function(job) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/run_appraisal_job_modal.html',
        controller: 'AppraisalJobModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            job,
            allow_close: true,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          vm.templatePipe(vm.templateTableState);
          vm.nextPipe(vm.nextTableState);
          vm.ongoingPipe(vm.ongoingTableState);
          vm.finishedPipe(vm.finishedTableState);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.createTemplateModal = function() {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/create_appraisal_modal.html',
        controller: 'AppraisalModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {},
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          vm.templatePipe(vm.templateTableState);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.createJobModal = function(template) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/create_appraisal_job_modal.html',
        controller: 'AppraisalJobModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: {
            template,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          vm.nextPipe(vm.nextTableState);
          vm.ongoingPipe(vm.ongoingTableState);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.editJob = function(job) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/edit_appraisal_job_modal.html',
        controller: 'AppraisalJobModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: {
            job,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          vm.nextPipe(vm.nextTableState);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.editAppraisalTemplateModal = function(appraisal) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/edit_appraisal_template_modal.html',
        controller: 'AppraisalModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            appraisal: appraisal,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          vm.templatePipe(vm.templateTableState);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    vm.removeAppraisalTemplateModal = function(appraisal) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_appraisal_template_modal.html',
        controller: 'AppraisalModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            appraisal: appraisal,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          vm.templatePipe(vm.templateTableState);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    vm.removeJob = function(job) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_appraisal_job_modal.html',
        controller: 'AppraisalJobModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            job,
            allow_close: true,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          vm.nextPipe(vm.nextTableState);
          vm.finishedPipe(vm.finishedTableState);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
  }
}
