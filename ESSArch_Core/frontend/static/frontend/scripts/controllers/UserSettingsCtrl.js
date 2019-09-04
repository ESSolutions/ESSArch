export default class UserSettingsCtrl {
  constructor(Me, $scope, $rootScope, $controller, myService, $window) {
    const vm = this;
    $controller('BaseCtrl', {$scope: $scope, vm: vm, ipSortString: '', params: {}});
    vm.activeColumns = {chosen: []};
    vm.availableColumns = {options: [], chosen: []};

    $scope.changeIpViewType = function(type) {
      Me.update({
        ip_list_view_type: type,
      }).$promise.then(function(data) {
        $window.sessionStorage.setItem('view-type', data.ip_list_view_type);
        $rootScope.auth = data;
      });
    };

    function loadColumnPicker() {
      vm.allColumns.forEach(function(column) {
        let tempBool = false;
        vm.activeColumns.options.forEach(function(activeColumn) {
          if (column == activeColumn) {
            tempBool = true;
          }
        });
        if (!tempBool) {
          vm.availableColumns.options.push(column);
        }
      });
    }

    myService.getActiveColumns().then(function(result) {
      vm.activeColumns.options = result.activeColumns;
      vm.allColumns = result.allColumns;
      loadColumnPicker();
    });
    $scope.moveToActive = function(inputArray) {
      inputArray.forEach(function(column) {
        vm.activeColumns.options.push(column);
        vm.availableColumns.options.splice(vm.availableColumns.options.indexOf(column), 1);
      });
      vm.availableColumns.chosen = [];
    };
    $scope.moveToAvailable = function(inputArray) {
      inputArray.forEach(function(column) {
        vm.availableColumns.options.push(column);
        vm.activeColumns.options.splice(vm.activeColumns.options.indexOf(column), 1);
      });
      vm.activeColumns.chosen = [];
    };
    $scope.moveUp = function(elements) {
      const A = vm.activeColumns.options;
      for (let i = 0; i < elements.length; i++) {
        const from = A.indexOf(elements[i]);
        if (A.indexOf(elements[i]) > i) {
          vm.activeColumns.options.move(from, from - 1);
        }
      }
    };

    $scope.moveDown = function(elements) {
      const A = vm.activeColumns.options;
      for (let i = elements.length - 1; i >= 0; i--) {
        const from = A.indexOf(elements[i]);
        if (A.indexOf(elements[i]) < A.length - (elements.length - i)) {
          vm.activeColumns.options.move(from, from + 1);
        }
      }
    };
    Array.prototype.move = function(from, to) {
      this.splice(to, 0, this.splice(from, 1)[0]);
    };
    $scope.saveColumns = function() {
      $rootScope.listViewColumns = vm.activeColumns.options;
      vm.activeColumns.chosen = [];
      $scope.saveAlert = null;
      const updateArray = vm.activeColumns.options.map(function(a) {
        return a.label;
      });
      Me.update({
        ip_list_columns: updateArray,
      }).$promise.then(
        function(data) {
          $rootScope.auth = data;
          $scope.saveAlert = $scope.alerts.saveSuccess;
        },
        function error() {
          $scope.saveAlert = $scope.alerts.saveError;
        }
      );
    };
    $scope.saveAlert = null;
    $scope.alerts = {
      saveError: {type: 'danger', msg: 'SAVE_ERROR'},
      saveSuccess: {type: 'success', msg: 'SAVED_MESSAGE'},
    };
    $scope.closeAlert = function() {
      $scope.saveAlert = null;
    };
  }
}
