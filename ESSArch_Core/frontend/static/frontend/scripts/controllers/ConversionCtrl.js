export default class {
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
    Conversion,
    $translate,
    $transitions,
    listViewService
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
      $interval.cancel(conversionInterval);
    });
    var conversionInterval = $interval(function() {
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
     * Smart table pipe function for conversion rules
     * @param {*} tableState
     */
    vm.rulePipe = function(tableState) {
      if (tableState && tableState.search.predicateObject) {
        var search = tableState.search.predicateObject['$'];
      }
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
        let paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.rulesPerPage);
        Conversion.getRules(paginationParams.pageNumber, paginationParams.number, sortString, search).then(function(
          response
        ) {
          tableState.pagination.numberOfPages = Math.ceil(response.count / paginationParams.number); //set the number of pages so the pagination can update
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
     * Smart table pipe function for ongoing conversions
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
        let paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.ongoingPerPage);
        Conversion.getOngoing(paginationParams.pageNumber, paginationParams.number, sortString, search).then(function(
          response
        ) {
          tableState.pagination.numberOfPages = Math.ceil(response.count / paginationParams.number); //set the number of pages so the pagination can update
          vm.ongoingTableState = tableState;
          vm.ongoing = response.data;
          $scope.ongoingLoading = false;
        });
      }
    };

    /**
     * Smart table pipe function for next conversions
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
        let paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.nextPerPage);
        Conversion.getNext(paginationParams.pageNumber, paginationParams.number, sortString, search).then(function(
          response
        ) {
          tableState.pagination.numberOfPages = Math.ceil(response.count / paginationParams.number); //set the number of pages so the pagination can update
          vm.nextTableState = tableState;
          vm.next = response.data;
          $scope.nextLoading = false;
        });
      }
    };

    /**
     * Smart table pipe function for finished conversions
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
        let paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.finishedPerPage);
        Conversion.getFinished(paginationParams.pageNumber, paginationParams.number, sortString, search).then(function(
          response
        ) {
          tableState.pagination.numberOfPages = Math.ceil(response.count / paginationParams.number); //set the number of pages so the pagination can update
          vm.finishedTableState = tableState;
          vm.finished = response.data;
          $scope.finishedLoading = false;
        });
      }
    };

    /**
     * Run conversion rule now
     * @param {Object} conversion
     */
    vm.runJob = function(job) {
      $http({
        url: appConfig.djangoUrl + 'conversion-jobs/' + job.id + '/run/',
        method: 'POST',
      }).then(function(response) {
        Notifications.add($translate.instant('ARCHIVE_MAINTENANCE.JOB_RUNNING'), 'success');
      });
    };

    /*
     * Array containing chosen(checked) conversion rules to use
     * as filter for the other conversion tables
     */
    vm.ruleFilters = [];

    /**
     * Add chosen conversion rule to list of filters or remove it.
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
     * Show conversion report
     * @param {Object} conversion
     */
    vm.showReport = function(conversion) {
      var file = $sce.trustAsResourceUrl(appConfig.djangoUrl + 'conversion-jobs/' + conversion.id + '/report/');
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
        templateUrl: 'static/frontend/views/preview_conversion_modal.html',
        controller: 'ConversionModalInstanceCtrl',
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
        templateUrl: 'static/frontend/views/create_conversion_modal.html',
        controller: 'ConversionModalInstanceCtrl',
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
        templateUrl: 'static/frontend/views/conversion_rule_modal.html',
        controller: 'ConversionModalInstanceCtrl',
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

    vm.ongoingModal = function(conversion) {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/conversion_modal.html',
        controller: 'ConversionModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            conversion: conversion,
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

    vm.nextModal = function(conversion) {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/conversion_modal.html',
        controller: 'ConversionModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            conversion: conversion,
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

    vm.finishedModal = function(conversion) {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/conversion_modal.html',
        controller: 'ConversionModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            conversion: conversion,
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
    vm.removeConversionRuleModal = function(conversion) {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_conversion_rule_modal.html',
        controller: 'ConversionModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            conversion: conversion,
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
