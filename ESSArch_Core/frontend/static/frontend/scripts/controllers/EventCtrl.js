export default class EventCtrl {
  constructor(
    Resource,
    $scope,
    $rootScope,
    listViewService,
    $interval,
    appConfig,
    $cookies,
    $window,
    $translate,
    $http,
    Notifications,
    $transitions,
    Filters,
    $timeout,
    $state
  ) {
    const vm = this;
    $scope.$translate = $translate;

    vm.getCookieName = function() {
      let name;
      switch ($rootScope.app) {
        case 'ESSArch Preservation Platform':
          name = 'epp-events-per-page';
          break;
        case 'ESSArch Tools For Producer':
          name = 'etp-events-per-page';
          break;
        case 'ESSArch Tools Archive':
          name = 'eta-events-per-page';
          break;
        default:
          name = 'etp-events-per-page';
          break;
      }
      return name;
    };

    vm.itemsPerPage = $cookies.get(vm.getCookieName) || 10;
    $scope.updateEventsPerPage = function(items) {
      $cookies.put(vm.getCookieName, items);
    };
    $scope.selected = [];
    vm.displayed = [];
    $scope.addEventAlert = null;
    $scope.alerts = {
      addEventError: {type: 'danger', msg: 'EVENT.ERROR_MESSAGE'},
      addEventSuccess: {type: 'success', msg: 'EVENT.EVENT_ADDED'},
    };
    vm.$onInit = function() {
      $scope.ip = vm.ip;
      vm.getEventlogData();
      vm.createFilterModel();
    };
    vm.$onChanges = function() {
      $scope.addEventAlert = null;
      $scope.ip = vm.ip;
      vm.getEventlogData();
      if ($scope.stCtrl) {
        $scope.stCtrl.pipe();
      }
    };
    //Get data for eventlog view
    vm.getEventlogData = function() {
      listViewService.getEventlogData().then(function(value) {
        vm.eventTypeCollection = value;
      });
    };

    $scope.closeAlert = function() {
      $scope.addEventAlert = null;
    };
    $transitions.onSuccess({}, function($transition) {
      $interval.cancel(eventInterval);
    });
    $scope.$on('$destroy', function() {
      $interval.cancel(eventInterval);
    });
    $scope.newEventForm = {
      eventType: '',
      eventOutcome: '',
      comment: '',
    };
    $scope.eventLevels = {
      0: 'success',
      1: 'failure',
    };
    $scope.getEventOutcome = function(outcome) {
      const level = $scope.eventLevels[outcome];
      return level;
    };
    $scope.eventOutcomes = (function() {
      const levels = $scope.eventLevels;
      return Object.keys(levels).map(function(k) {
        return {value: k, name: levels[k]};
      });
    })();
    //Event click funciton
    $scope.eventClick = function(row) {
      if (row.class == 'selected') {
        row.class = '';
        for (let i = 0; i < $scope.selected.length; i++) {
          if ($scope.selected[i].id === row.id) {
            $scope.selected.splice(i, 1);
          }
        }
      } else {
        row.class = 'selected';
        $scope.selected.push(row);
      }
    };
    $scope.addEvent = function(ip, eventType, eventDetail, eventOutcome) {
      $scope.addEventAlert = null;
      listViewService
        .addEvent(ip, eventType, eventDetail, eventOutcome)
        .then(function(value) {
          $scope.stCtrl.pipe();
          $scope.newEventForm = {
            eventType: '',
            eventOutcome: '',
            comment: '',
          };
          Notifications.add($translate.instant('EVENT.EVENT_ADDED'), 'success');
        })
        .catch(function error() {
          Notifications.add($translate.instant('EVENT.ERROR_MESSAGE'), 'error');
        });
    };
    let eventInterval;
    function updateEvents() {
      $interval.cancel(eventInterval);
      eventInterval = $interval(function() {
        $scope.stCtrl.pipe();
      }, appConfig.eventInterval);
    }
    updateEvents();
    //Get data from rest api for event table
    $scope.eventPipe = function(tableState, ctrl) {
      $scope.eventLoading = true;
      if (vm.displayed.length == 0) {
        $scope.initLoad = true;
      }
      var search = '';
      if (tableState.search.predicateObject) {
        var search = tableState.search.predicateObject['$'];
      }
      $scope.stCtrl = ctrl;
      const sorting = tableState.sort;
      const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.itemsPerPage);

      Resource.getEventPage(
        paginationParams.start,
        paginationParams.number,
        paginationParams.pageNumber,
        tableState,
        $scope.selected,
        sorting,
        $scope.columnFilters,
        search
      )
        .then(function(result) {
          vm.displayed = result.data;
          tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
          $scope.tableState = tableState;
          $scope.eventLoading = false;
          $scope.initLoad = false;
        })
        .catch(function(response) {
          if (response.status === 404) {
            listViewService.checkPages('events', paginationParams.number, $scope.columnFilters).then(function(result) {
              tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
              tableState.pagination.start = result.numberOfPages * paginationParams.number - paginationParams.number;
              $scope.stCtrl.pipe();
            });
          }
        });
    };
    //advanced filter form data
    $scope.columnFilters = {};
    $scope.filterModel = {};
    $scope.options = {};
    $scope.fields = [];

    vm.createFilterModel = () => {
      let model = Filters.getEventFilters($state.current.name).model;
      $scope.filterModel = angular.copy(model);
      vm.initialColumnFilters = angular.copy(model);
      $scope.columnFilters = angular.copy(model);
    };

    vm.createFilterFields = () => {
      $scope.fields = Filters.getEventFilters($state.current.name).fields;
    };

    //Toggle visibility of advanced filters
    $scope.toggleAdvancedFilters = function() {
      if ($scope.showAdvancedFilters) {
        $scope.showAdvancedFilters = false;
      } else {
        if ($scope.fields.length <= 0) {
          vm.createFilterFields();
        }
        $scope.showAdvancedFilters = true;
      }
      if ($scope.showAdvancedFilters) {
        $window.onclick = function(event) {
          const clickedElement = $(event.target);
          if (!clickedElement) return;
          const elementClasses = event.target.classList;
          const clickedOnAdvancedFilters =
            elementClasses.contains('filter-icon') ||
            elementClasses.contains('advanced-filters') ||
            elementClasses.contains('ui-select-match-text') ||
            elementClasses.contains('ui-select-search') ||
            elementClasses.contains('ui-select-toggle') ||
            elementClasses.contains('ui-select-choices') ||
            clickedElement.parents('.advanced-filters').length ||
            clickedElement.parents('.button-group').length;

          if (!clickedOnAdvancedFilters) {
            $scope.showAdvancedFilters = !$scope.showAdvancedFilters;
            $window.onclick = null;
            $scope.$apply();
          }
        };
      } else {
        $window.onclick = null;
      }
    };

    vm.clearFilters = function() {
      vm.createFilterModel();
      vm.createFilterFields();
      $scope.submitAdvancedFilters();
    };

    $scope.clearSearch = function() {
      delete $scope.tableState.search.predicateObject;
      $('#event-search-input')[0].value = '';
      $scope.stCtrl.pipe();
    };

    $scope.filterActive = function() {
      let temp = false;
      for (const key in $scope.columnFilters) {
        if (
          (angular.isUndefined(vm.initialColumnFilters[key]) &&
            $scope.columnFilters[key] !== '' &&
            $scope.columnFilters[key] !== null) ||
          (!angular.isUndefined(vm.initialColumnFilters[key]) &&
            $scope.columnFilters[key] !== vm.initialColumnFilters[key])
        ) {
          temp = true;
        }
      }
      return temp;
    };

    $scope.submitAdvancedFilters = function() {
      $scope.columnFilters = angular.copy($scope.filterModel);
      $scope.stCtrl.pipe();
    };

    // Click function for request form submit.
    // Replaced form="vm.requestForm" to work in IE
    $scope.clickSubmit = function() {
      if (vm.requestForm.$valid) {
        $scope.submitRequest($scope.ip, vm.request);
      }
    };
  }
}
