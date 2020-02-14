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
      $interval.cancel(conversionInterval);
    });
    var conversionInterval = $interval(function() {
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
     * Smart table pipe function for conversion templates
     * @param {*} tableState
     */
    vm.templatePipe = function(tableState) {
      if (tableState && tableState.search.predicateObject) {
        var search = tableState.search.predicateObject['$'];
      }
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
        Conversion.getTemplates(paginationParams, sortString, search).then(function(response) {
          tableState.pagination.numberOfPages = Math.ceil(response.count / paginationParams.number); //set the number of pages so the pagination can update
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
        const sorting = tableState.sort;
        let sortString = sorting.predicate;
        if (sorting.reverse) {
          sortString = '-' + sortString;
        }
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.ongoingPerPage);
        Conversion.getOngoing(paginationParams, sortString, search).then(function(response) {
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
        const sorting = tableState.sort;
        let sortString = sorting.predicate;
        if (sorting.reverse) {
          sortString = '-' + sortString;
        }
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.nextPerPage);
        Conversion.getNext(paginationParams, sortString, search).then(function(response) {
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
        const sorting = tableState.sort;
        let sortString = sorting.predicate;
        if (sorting.reverse) {
          sortString = '-' + sortString;
        }
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.finishedPerPage);
        Conversion.getFinished(paginationParams, sortString, search).then(function(response) {
          tableState.pagination.numberOfPages = Math.ceil(response.count / paginationParams.number); //set the number of pages so the pagination can update
          vm.finishedTableState = tableState;
          vm.finished = response.data;
          $scope.finishedLoading = false;
        });
      }
    };

    /**
     * Run conversion template now
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
     * Array containing chosen(checked) conversion templates to use
     * as filter for the other conversion tables
     */
    vm.templateFilters = [];

    /**
     * Add chosen conversion template to list of filters or remove it.
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
     * Show conversion report
     * @param {Object} conversion
     */
    vm.showReport = function(conversion) {
      const file = $sce.trustAsResourceUrl(appConfig.djangoUrl + 'conversion-jobs/' + conversion.id + '/report/');
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

    vm.previewModal = function(job) {
      const modalInstance = $uibModal.open({
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
        templateUrl: 'static/frontend/views/create_conversion_modal.html',
        controller: 'ConversionModalInstanceCtrl',
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

    vm.templateModal = function(template) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/conversion_template_modal.html',
        controller: 'ConversionModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            template: template,
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
      const modalInstance = $uibModal.open({
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
      const modalInstance = $uibModal.open({
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
      const modalInstance = $uibModal.open({
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
    vm.removeConversionTemplateModal = function(conversion) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_conversion_template_modal.html',
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
          vm.templatePipe(vm.templateTableState);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
  }
}
