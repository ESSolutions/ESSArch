export default class LocationModalInstanceCtrl {
  constructor($scope, $http, appConfig, $translate, data, $uibModalInstance, $q, EditMode, Utils, $rootScope) {
    const $ctrl = this;
    $ctrl.location = {};
    $ctrl.fields = [];
    $ctrl.options = {};
    $ctrl.$onInit = function() {
      if (!angular.isUndefined(data.location) && data.location !== null) {
        $ctrl.location = angular.copy(data.location);
        if (data.remove) {
          return;
        } else {
          $ctrl.location.metric = data.location.metric ? angular.copy(data.location.metric.id) : null;
          $ctrl.location.level_type = angular.copy(data.location.level_type.id);
          $ctrl.location.function = angular.copy(data.location.function.id);
        }
      }
      EditMode.enable();
      $ctrl.buildForm();
    };

    $ctrl.getMetrics = function() {
      return $http.get(appConfig.djangoUrl + 'metric-types/', {params: {pager: 'none'}}).then(function(response) {
        $ctrl.options.metric = response.data;
        return response.data;
      });
    };
    $ctrl.getLevelTypes = function() {
      return $http
        .get(appConfig.djangoUrl + 'location-level-types/', {params: {pager: 'none'}})
        .then(function(response) {
          $ctrl.options.levelType = response.data;
          return response.data;
        });
    };
    $ctrl.getFunctionTypes = function() {
      return $http
        .get(appConfig.djangoUrl + 'location-function-types/', {params: {pager: 'none'}})
        .then(function(response) {
          $ctrl.options.functionType = response.data;
          return response.data;
        });
    };
    $ctrl.buildForm = function() {
      const promises = [];
      promises.push(
        $ctrl.getMetrics().then(function(profiles) {
          return profiles;
        })
      );
      promises.push(
        $ctrl.getLevelTypes().then(function(levels) {
          return levels;
        })
      );
      promises.push(
        $ctrl.getFunctionTypes().then(function(functions) {
          return functions;
        })
      );
      $q.all(promises).then(function(responses) {
        $ctrl.fields = [
          {
            type: 'input',
            key: 'name',
            templateOptions: {
              required: true,
              label: $translate.instant('NAME'),
            },
          },
          {
            type: 'select',
            key: 'metric',
            templateOptions: {
              label: $translate.instant('ACCESS.METRIC'),
              options: $ctrl.options.metric,
              labelProp: 'name',
              valueProp: 'id',
              defaultValue: $ctrl.options.metric.length > 0 ? $ctrl.options.metric[0].id : null,
            },
          },
          {
            type: 'input',
            key: 'capacity',
            templateOptions: {
              type: 'number',
              label: $translate.instant('ACCESS.CAPACITY'),
            },
          },
          {
            type: 'select',
            key: 'level_type',
            templateOptions: {
              label: $translate.instant('ACCESS.LEVEL'),
              options: $ctrl.options.levelType,
              required: true,
              labelProp: 'name',
              valueProp: 'id',
              defaultValue: $ctrl.options.levelType.length > 0 ? $ctrl.options.levelType[0].id : null,
              notNull: true,
            },
          },
          {
            type: 'select',
            key: 'function',
            templateOptions: {
              label: $translate.instant('ACCESS.LOCATION_FUNCTION'),
              options: $ctrl.options.functionType,
              required: true,
              labelProp: 'name',
              valueProp: 'id',
              defaultValue: $ctrl.options.functionType.length > 0 ? $ctrl.options.functionType[0].id : null,
              notNull: true,
            },
          },
        ];
      });
    };

    $ctrl.add = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      if (data.parent) {
        $ctrl.location.parent = data.parent;
      } else {
        $ctrl.location.parent = null;
      }
      $ctrl.adding = true;
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'locations/',
        method: 'POST',
        data: $ctrl.location,
      })
        .then(function(response) {
          $ctrl.adding = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.adding = false;
          $ctrl.nonFieldErrors = response.data.non_field_errors;
        });
    };

    $ctrl.edit = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.saving = true;
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'locations/' + data.location.id + '/',
        method: 'PATCH',
        data: Utils.getDiff(data.location, $ctrl.location, {map: {metric: 'id', function: 'id', level_type: 'id'}}),
      })
        .then(function(response) {
          $ctrl.saving = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.saving = false;
          $ctrl.nonFieldErrors = response.data.non_field_errors;
        });
    };

    $ctrl.remove = function() {
      $ctrl.removing = true;
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'locations/' + data.location.id + '/',
        method: 'DELETE',
      })
        .then(function(response) {
          $uibModalInstance.close(response.data);
          $ctrl.removing = false;
        })
        .catch(function(response) {
          if (response.data && response.data.detail) {
            $ctrl.nonFieldErrors = [response.data.detail];
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
        const message = $translate.instant('UNSAVED_DATA_WARNING');
        if (!confirm(message)) {
          event.preventDefault();
        } else {
          EditMode.disable();
        }
      }
    });
  }
}
