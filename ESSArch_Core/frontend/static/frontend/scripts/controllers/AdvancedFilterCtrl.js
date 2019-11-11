export default class AdvancedFilterCtrl {
  constructor($scope, Filters, $timeout, $state, $window, $transitions) {
    const vm = this;
    vm.model = null;
    vm.initialColumnFilters = {};
    vm.model = {};
    vm.options = {};
    vm.fields = [];
    vm.showAdvancedFilters = false;
    const currentState = $state.current.name;

    vm.$onInit = () => {
      if (
        vm.type &&
        (angular.isUndefined(vm.activeModel) || vm.activeModel === null || angular.equals(vm.activeModel, {}))
      ) {
        vm.createFilterModel();
      } else if (vm.type) {
        vm.createFilterModel(angular.copy(vm.activeModel));
      }
    };

    const getModel = () => {
      switch (vm.type) {
        case 'ip':
          return Filters.getIpFilters(currentState).model;
        case 'event':
          return Filters.getEventFilters(currentState).model;
        case 'medium':
          return Filters.getStorageMediumFilters(currentState).model;
      }
    };

    const getFields = () => {
      switch (vm.type) {
        case 'ip':
          return Filters.getIpFilters(currentState).fields;
        case 'event':
          return Filters.getEventFilters(currentState).fields;
        case 'medium':
          return Filters.getStorageMediumFilters(currentState).fields;
      }
    };

    vm.createFilterModel = initialValue => {
      let model = getModel();
      if (!angular.isUndefined(initialValue)) {
        model = angular.extend(model, initialValue);
      }
      vm.model = angular.copy(model);
      vm.initialColumnFilters = angular.copy(model);
      vm.activeModel = angular.copy(model);
    };

    vm.createFilterFields = () => {
      const fields = getFields();
      vm.fields = angular.copy(fields);
    };

    vm.clearFilters = function() {
      vm.createFilterModel();
      vm.createFilterFields();
      vm.submitAdvancedFilters();
    };

    //Toggle visibility of advanced filters
    vm.toggleAdvancedFilters = function() {
      if (vm.showAdvancedFilters) {
        vm.showAdvancedFilters = false;
      } else {
        if (!vm.fields || vm.fields.length <= 0) {
          vm.createFilterFields();
        }
        vm.showAdvancedFilters = true;
      }
      if (vm.showAdvancedFilters) {
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
            vm.showAdvancedFilters = !vm.showAdvancedFilters;
            $window.onclick = null;
            $scope.$apply();
          }
        };
      } else {
        $window.onclick = null;
      }
    };

    vm.filterActive = function() {
      let temp = false;
      for (const key in vm.activeModel) {
        if (
          (angular.isUndefined(vm.initialColumnFilters[key]) &&
            vm.activeModel[key] !== '' &&
            vm.activeModel[key] !== null) ||
          (!angular.isUndefined(vm.initialColumnFilters[key]) && vm.activeModel[key] !== vm.initialColumnFilters[key])
        ) {
          temp = true;
        }
      }
      return temp;
    };

    vm.submitAdvancedFilters = function() {
      if (vm.filterForm.$invalid) {
        vm.filterForm.$setSubmitted();
        return;
      }
      vm.activeModel = angular.copy(vm.model);
      if (!angular.isUndefined(vm.update)) {
        $timeout(() => {
          vm.update();
        });
      }
    };
  }
}
