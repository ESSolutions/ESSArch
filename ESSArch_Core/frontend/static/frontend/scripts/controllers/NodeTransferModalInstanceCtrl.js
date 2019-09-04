export default class NodeTransferModalInstanceCtrl {
  constructor($scope, data, $uibModalInstance, appConfig, $http, EditMode, $translate) {
    var $ctrl = this;
    $ctrl.transfer = null;

    $ctrl.$onInit = function() {
      EditMode.enable();
      if (!angular.isUndefined(data.node)) {
        $ctrl.node = angular.copy(data.node);
      }
      if (data.transfer !== null && !angular.isUndefined(data.transfer)) {
        $ctrl.transfer = angular.copy(data.transfer);
      }
      if (data.nodes) {
        $ctrl.nodes = $ctrl.filterNodes(angular.copy(data.nodes));
      }
    };

    $ctrl.filterNodes = function(nodes) {
      var filtered = [];
      nodes.forEach(function(x) {
        if (
          !angular.isUndefined(x) &&
          x._is_structure_unit !== true &&
          x._index !== 'archive' &&
          x.placeholder !== true &&
          x.type !== 'agent'
        ) {
          filtered.push(x);
        }
      });
      return filtered;
    };

    $ctrl.cleartransfer = function() {
      $ctrl.transfer = null;
    };

    $ctrl.filterNodesByType = function(nodes) {
      var obj = {
        tags: [],
        structure_units: [],
      };
      nodes.forEach(function(x) {
        if (!x.id) {
          x.id = x._id;
        }
        if (x.is_unit_leaf_node || (!x.is_unit_leaf_node && !x.is_leaf_node)) {
          obj.structure_units.push(x.id);
        } else {
          obj.tags.push(x.id);
        }
      });
      return obj;
    };

    $ctrl.remove = function() {
      $ctrl.saving = true;
      var nodes = [];
      if (data.node) {
        nodes = [angular.copy(data.node)];
      } else if (data.nodes) {
        nodes = angular.copy(data.nodes);
      }
      $http
        .post(appConfig.djangoUrl + 'transfers/' + data.transfer.id + '/remove-nodes/', $ctrl.filterNodesByType(nodes))
        .then(function(response) {
          $ctrl.saving = false;
          EditMode.disable();
          $uibModalInstance.close('removed');
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.saving = false;
        });
    };

    $ctrl.cancel = function() {
      EditMode.disable();
      $uibModalInstance.dismiss();
    };

    $scope.$on('modal.closing', function(event, reason, closed) {
      if (
        (data.allow_close === null || angular.isUndefined(data.allow_close) || data.allow_close !== true) &&
        (reason === 'cancel' || reason === 'backdrop click' || reason === 'escape key press')
      ) {
        var message = $translate.instant('UNSAVED_DATA_WARNING');
        if (!confirm(message)) {
          event.preventDefault();
        } else {
          EditMode.disable();
        }
      }
    });
  }
}
