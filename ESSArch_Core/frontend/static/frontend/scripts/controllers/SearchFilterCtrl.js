export default class SearchFilterCtrl {
  constructor($scope, $window, $rootScope) {
    const vm = this;
    let onclickSet = false;
    vm.q = '';
    vm.$onInit = function() {
      if (vm.ngModel === '' || vm.ngModel === null || angular.isUndefined(vm.ngModel)) {
        vm.selected = [];
      } else {
        vm.selected = vm.ngModel;
      }
      if (vm.ngChange && vm.selected.length > 0) {
        vm.ngChange();
      }
    };

    $rootScope.$on('CLOSE_FILTERS', function(e, data) {
      if (data.except !== $scope.$id) {
        vm.resultListVisible = false;
        onclickSet = false;
      }
    });

    $scope.$watch(
      function() {
        return vm.ngModel;
      },
      function(newval, oldval) {
        if (newval === '' || newval === null || angular.isUndefined(newval)) {
          vm.selected = [];
        } else {
          vm.selected = newval;
        }
      }
    );

    vm.search = function() {
      vm.update({
        search: vm.q,
      });
    };
    vm.updateModel = function() {
      if (vm.selected.length <= 0) {
        vm.ngModel = null;
      } else {
        vm.ngModel = vm.selected;
      }
      if (!angular.isUndefined(vm.ngChange)) {
        vm.ngChange();
      }
    };

    vm.select = function(item) {
      vm.selected.push(item);
      vm.updateModel();
      vm.resultListVisible = false;
    };

    vm.deselect = function(item) {
      vm.selected.forEach(function(x, idx, array) {
        if (x[vm.valueProp] === item[vm.valueProp]) {
          array.splice(idx, 1);
        }
      });
      vm.updateModel();
    };
    vm.notSelected = function(item) {
      let notSelected = true;
      vm.selected.forEach(function(x) {
        if (x[vm.valueProp] === item[vm.valueProp]) {
          notSelected = false;
        }
      });
      return notSelected;
    };

    vm.optionsEmpty = function() {
      const list = angular.copy(vm.options);
      const toDelete = [];
      list.forEach(function(x, idx, array) {
        if (!vm.notSelected(x)) {
          toDelete.push(idx);
        }
      });
      for (let i = toDelete.length; i > 0; i--) {
        list.splice(toDelete[i], 1);
      }
      return list.length <= 0;
    };
    vm.openOptions = function(evt) {
      vm.resultListVisible = true;
      vm.search();
      if ($window.onclick && !onclickSet) {
        $rootScope.$broadcast('CLOSE_FILTERS', {except: $scope.$id});
      }
      onclickSet = true;
      $window.onclick = function(event) {
        const clickedElement = $(event.target);
        if (!clickedElement) return;
        const elementClasses = event.target.classList;
        const clickedOnFilter =
          elementClasses.contains('filter-' + $scope.$id) ||
          elementClasses.contains('filter-options-item') ||
          clickedElement.parents('filter-options').length;

        if (!clickedOnFilter) {
          vm.resultListVisible = false;
          $window.onclick = null;
          onclickSet = false;
          $scope.$apply();
        }
      };
    };
  }
}
