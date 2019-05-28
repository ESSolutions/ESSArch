export default class AppraisalCtrl {
  constructor(
    ArchivePolicy,
    $scope,
    $controller,
    $rootScope,
    $cookies,
    $stateParams,
    appConfig,
    $http,
    $timeout,
    $uibModal,
    $log,
    $sce,
    $window,
    Notifications,
    $filter,
    $interval,
    Appraisal,
    $translate,
    $transitions
  ) {
    var vm = this;
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
        var sorting = tableState.sort;
        var sortString = sorting.predicate;
        if (sorting.reverse) {
          sortString = '-' + sortString;
        }
        var pagination = tableState.pagination;
        var start = pagination.start || 0; // This is NOT the page number, but the index of item in the list that you want to use to display the table.
        var number = pagination.number || vm.rulesPerPage; // Number of entries showed per page.
        var pageNumber = start / number + 1;
        Appraisal.getRules(pageNumber, number, sortString, search).then(function(response) {
          tableState.pagination.numberOfPages = Math.ceil(response.count / number); //set the number of pages so the pagination can update
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
        var sorting = tableState.sort;
        var sortString = sorting.predicate;
        if (sorting.reverse) {
          sortString = '-' + sortString;
        }
        var pagination = tableState.pagination;
        var start = pagination.start || 0; // This is NOT the page number, but the index of item in the list that you want to use to display the table.
        var number = pagination.number || vm.ongoingPerPage; // Number of entries showed per page.
        var pageNumber = start / number + 1;
        Appraisal.getOngoing(pageNumber, number, sortString, search).then(function(response) {
          tableState.pagination.numberOfPages = Math.ceil(response.count / number); //set the number of pages so the pagination can update
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
        var sorting = tableState.sort;
        var sortString = sorting.predicate;
        if (sorting.reverse) {
          sortString = '-' + sortString;
        }
        var pagination = tableState.pagination;
        var start = pagination.start || 0; // This is NOT the page number, but the index of item in the list that you want to use to display the table.
        var number = pagination.number || vm.nextPerPage; // Number of entries showed per page.
        var pageNumber = start / number + 1;
        Appraisal.getNext(pageNumber, number, sortString, search).then(function(response) {
          tableState.pagination.numberOfPages = Math.ceil(response.count / number); //set the number of pages so the pagination can update
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
        var sorting = tableState.sort;
        var sortString = sorting.predicate;
        if (sorting.reverse) {
          sortString = '-' + sortString;
        }
        var pagination = tableState.pagination;
        var start = pagination.start || 0; // This is NOT the page number, but the index of item in the list that you want to use to display the table.
        var number = pagination.number || vm.finishedPerPage; // Number of entries showed per page.
        var pageNumber = start / number + 1;
        Appraisal.getFinished(pageNumber, number, sortString, search).then(function(response) {
          tableState.pagination.numberOfPages = Math.ceil(response.count / number); //set the number of pages so the pagination can update
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
      var file = $sce.trustAsResourceUrl(appConfig.djangoUrl + 'appraisal-jobs/' + appraisal.id + '/report/');
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
      var modalInstance = $uibModal.open({
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
      var modalInstance = $uibModal.open({
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
      var modalInstance = $uibModal.open({
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
      var modalInstance = $uibModal.open({
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
      var modalInstance = $uibModal.open({
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
      var modalInstance = $uibModal.open({
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
      var modalInstance = $uibModal.open({
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
};
