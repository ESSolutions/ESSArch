angular
  .module('essarch.controllers')
  .controller('NodeLocationModalInstanceCtrl', function(
    $scope,
    data,
    $uibModalInstance,
    appConfig,
    $http,
    EditMode,
    Search,
    $translate,
    $q,
    Notifications
  ) {
    var $ctrl = this;
    $ctrl.location = null;

    $ctrl.$onInit = function() {
      EditMode.enable();
      if (!angular.isUndefined(data.node)) {
        $ctrl.node = angular.copy(data.node);
        if (data.remove_link === true) {
          $ctrl.node.location = null;
        }
      }
      EditMode.enable();
      if (data.location !== null && !angular.isUndefined(data.location)) {
        $ctrl.location = angular.copy(data.location);
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

    $ctrl.clearLocation = function() {
      $ctrl.location = null;
    };

    $ctrl.save = function() {
      $ctrl.saving = true;
      if (data.node) {
        Search.updateNode(data.node, {location: $ctrl.location !== null ? $ctrl.location.id : null})
          .then(function(response) {
            $ctrl.saving = false;
            EditMode.disable();
            Notifications.add($translate.instant('ACCESS.LOCATION_LINK_SUCCESS'), 'success');
            $uibModalInstance.close('edited');
          })
          .catch(function(response) {
            $ctrl.nonFieldErrors = response.data.non_field_errors;
            $ctrl.saving = false;
          });
      } else if (data.nodes) {
        var promises = [];
        $ctrl.nodes.forEach(function(node) {
          promises.push(
            Search.updateNode(node, {location: $ctrl.location !== null ? $ctrl.location.id : null}).then(function(
              response
            ) {
              return response;
            })
          );
        });
        $q.all(promises)
          .then(function(responses) {
            $ctrl.saving = false;
            EditMode.disable();
            Notifications.add($translate.instant('ACCESS.LOCATION_LINK_SUCCESS'), 'success');
            $uibModalInstance.close('edited');
          })
          .catch(function(responses) {
            responses.forEach(function(response) {
              $ctrl.nonFieldErrors = response.data.non_field_errors;
              $ctrl.saving = false;
            });
            $ctrl.saving = false;
          });
      }
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
  });
