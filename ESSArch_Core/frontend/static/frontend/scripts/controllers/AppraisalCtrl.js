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
    vm.rulesPerPage = 10;
    vm.ongoingPerPage = 10;
    vm.nextPerPage = 10;
    vm.finishedPerPage = 10;
    $scope.ruleLoading = false;
    $scope.ongoingLoading = false;
    $scope.nextLoading = false;
    $scope.finishedLoading = false;

    $scope.$translate = $translate;

    //Cancel update intervals on state change
    $transitions.onSuccess({}, function($transition) {
      $interval.cancel(appraisalInterval);
    });
    var appraisalInterval = $interval(function() {
      vm.rulePipe(vm.ruleTableState);
      vm.nextPipe(vm.nextTableState);
      vm.ongoingPipe(vm.ongoingTableState);
      vm.finishedPipe(vm.finishedTableState);
    }, appConfig.ipInterval);

    $scope.$on('REFRESH_LIST_VIEW', function(event, data) {
      vm.rulePipe(vm.ruleTableState);
      vm.nextPipe(vm.nextTableState);
      vm.ongoingPipe(vm.ongoingTableState);
      vm.finishedPipe(vm.finishedTableState);
    });

    /**
     * Smart table pipe function for appraisal rules
     * @param {*} tableState
     */
    vm.rulePipe = function(tableState) {
      $scope.ruleLoading = true;
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
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.rulesPerPage);
        Appraisal.getRules(paginationParams, sortString, search).then(function(response) {
          tableState.pagination.numberOfPages = Math.ceil(response.count / paginationParams.number); //set the number of pages so the pagination can update
          tableState.pagination.totalItemCount = response.count;
          vm.ruleTableState = tableState;
          vm.ruleFilters.forEach(function(x) {
            response.data.forEach(function(rule) {
              if (x == rule.id) {
                rule.usedAsFilter = true;
              }
            });
          });
          vm.rules = response.data;
          $scope.ruleLoading = false;
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

    /**
     * Run appraisal rule now
     * @param {Object} appraisal
     */
    vm.runJob = function(job) {
      $http({
        url: appConfig.djangoUrl + 'appraisal-jobs/' + job.id + '/run/',
        method: 'POST',
      }).then(function(response) {
        Notifications.add($translate.instant('ARCHIVE_MAINTENANCE.JOB_RUNNING'), 'success');
      });
    };

    /*
     * Array containing chosen(checked) appraisal rules to use
     * as filter for the other appraisal tables
     */
    vm.ruleFilters = [];

    /**
     * Add chosen appraisal rule to list of filters or remove it.
     * Connected to apprailsal rule table checkbox
     * @param {Object} rule
     */
    vm.useAsFilter = function(rule) {
      if (!vm.ruleFilters.includes(rule.id)) {
        rule.used_as_filter = true;
        vm.ruleFilters.push(rule.id);
      } else {
        vm.ruleFilters.splice(vm.ruleFilters.indexOf(rule.id), 1);
        rule.used_as_filter = false;
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
      delete vm.ruleTableState.search.predicateObject;
      $('#search-input')[0].value = '';
      vm.rulePipe();
    };
    /**
     * MODALS
     */

    vm.previewModal = function(job) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/preview_appraisal_modal.html',
        controller: 'AppraisalModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            preview: true,
            job: job,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          vm.runJob(job);
          vm.rulePipe(vm.ruleTableState);
          vm.nextPipe(vm.nextTableState);
          vm.ongoingPipe(vm.ongoingTableState);
          vm.finishedPipe(vm.finishedTableState);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.createRuleModal = function() {
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
          vm.rulePipe(vm.ruleTableState);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.ruleModal = function(rule) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/appraisal_rule_modal.html',
        controller: 'AppraisalModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            rule: rule,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {},
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.ongoingModal = function(appraisal) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/appraisal_modal.html',
        controller: 'AppraisalModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            appraisal: appraisal,
            state: 'Ongoing',
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {},
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.nextModal = function(appraisal) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/appraisal_modal.html',
        controller: 'AppraisalModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            appraisal: appraisal,
            state: 'Next',
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {},
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.finishedModal = function(appraisal) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/appraisal_modal.html',
        controller: 'AppraisalModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            appraisal: appraisal,
            state: 'Finished',
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {},
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    vm.removeAppraisalRuleModal = function(appraisal) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_appraisal_rule_modal.html',
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
          vm.rulePipe(vm.ruleTableState);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
  }
}
