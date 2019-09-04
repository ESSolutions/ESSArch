export default class NodeIdentifierModalInstanceCtrl {
  constructor($uibModalInstance, $scope, $translate, $http, appConfig, data, EditMode, $rootScope) {
    var $ctrl = this;
    $ctrl.identifier = {};
    $ctrl.fields = [];
    $ctrl.options = {};

    $ctrl.resetIdentifier = function(initialValue) {
      if (initialValue) {
        $ctrl.identifier = initialValue;
      } else {
        $ctrl.identifier = {};
      }
    };

    $ctrl.$onInit = function() {
      if (data.remove) {
        $ctrl.identifier = angular.copy(data.identifier);
      } else {
        return $http({
          url: appConfig.djangoUrl + 'node-identifier-types/',
          params: {pager: 'none'},
          method: 'GET',
        }).then(function(response) {
          $ctrl.options = {type: response.data};
          EditMode.enable();
          if (data.identifier) {
            var identifier = angular.copy(data.identifier);
            identifier.type = data.identifier.type.id;
            $ctrl.identifier = angular.copy(identifier);
          } else {
            var initialValue = $ctrl.options.type.length >= 1 ? {type: $ctrl.options.type[0].id} : {};
            $ctrl.resetIdentifier(initialValue);
          }
          $ctrl.loadForm();
        });
      }
    };

    $ctrl.loadForm = function() {
      $ctrl.fields = [
        {
          type: 'select',
          key: 'type',
          templateOptions: {
            label: $translate.instant('TYPE'),
            options: $ctrl.options.type,
            required: true,
            labelProp: 'name',
            valueProp: 'id',
            defaultValue: $ctrl.options.type[0].id,
            notNull: true,
          },
        },
        {
          type: 'input',
          key: 'identifier',
          templateOptions: {
            label: $translate.instant('ACCESS.IDENTIFIER'),
            required: true,
          },
        },
      ];
    };

    $ctrl.add = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.adding = true;
      var identifiers = angular.copy(data.node.identifiers);
      identifiers.forEach(function(x) {
        x.type = x.type.id;
      });
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'search/' + data.node.id + '/',
        method: 'PATCH',
        data: {identifiers: [$ctrl.identifier].concat(identifiers)},
      })
        .then(function(response) {
          $ctrl.adding = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          if (response.data.identifiers) {
            if (angular.isArray($ctrl.nonFieldErrors)) {
              $ctrl.nonFieldErrors = $ctrl.nonFieldErrors.concat(response.data.identifiers);
            } else {
              $ctrl.nonFieldErrors = response.data.identifiers;
            }
          }
          $ctrl.adding = false;
        });
    };
    $ctrl.save = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.saving = true;
      var identifiers = angular.copy(data.node.identifiers);
      identifiers.forEach(function(x, idx, array) {
        if (typeof x.type === 'object') {
          x.type = x.type.id;
        }
        if (x.id === $ctrl.identifier.id) {
          array[idx] = $ctrl.identifier;
        }
      });
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'search/' + data.node.id + '/',
        method: 'PATCH',
        data: {identifiers: identifiers},
      })
        .then(function(response) {
          $ctrl.saving = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          if (response.data.identifiers) {
            if (angular.isArray($ctrl.nonFieldErrors)) {
              $ctrl.nonFieldErrors = $ctrl.nonFieldErrors.concat(response.data.identifiers);
            } else {
              $ctrl.nonFieldErrors = response.data.identifiers;
            }
          }
          $ctrl.saving = false;
        });
    };

    $ctrl.remove = function() {
      $ctrl.removing = true;
      var toRemove = null;
      var identifiers = angular.copy(data.node.identifiers);
      identifiers.forEach(function(x, idx, array) {
        if (typeof x.type === 'object') {
          x.type = x.type.id;
        }
        if (x.id === $ctrl.identifier.id) {
          toRemove = idx;
        }
      });
      if (toRemove !== null) {
        identifiers.splice(toRemove, 1);
      }
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'search/' + data.node.id + '/',
        method: 'PATCH',
        data: {identifiers: identifiers},
      })
        .then(function(response) {
          $ctrl.removing = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          if (response.data.identifiers) {
            if (angular.isArray($ctrl.nonFieldErrors)) {
              $ctrl.nonFieldErrors = $ctrl.nonFieldErrors.concat(response.data.identifiers);
            } else {
              $ctrl.nonFieldErrors = response.data.identifiers;
            }
          }
          $ctrl.removing = false;
        });
    };

    $ctrl.cancel = function() {
      EditMode.disable();
      $uibModalInstance.dismiss('cancel');
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
