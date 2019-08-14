angular
  .module('essarch.controllers')
  .controller('AgentPlaceModalInstanceCtrl', function(
    $uibModalInstance,
    $scope,
    $translate,
    $http,
    appConfig,
    data,
    EditMode,
    $rootScope
  ) {
    var $ctrl = this;
    $ctrl.place;
    $ctrl.topography = {};
    $ctrl.placeTemplate = {};
    $ctrl.fields = [];
    $ctrl.resetPlace = function() {
      $ctrl.place = angular.copy($ctrl.placeTemplate);
    };

    $ctrl.$onInit = function() {
      return $http({
        url: appConfig.djangoUrl + 'agent-place-types/',
        params: {pager: 'none'},
        method: 'GET',
      }).then(function(response) {
        $ctrl.options = {type: response.data};
        EditMode.enable();
        if (data.place) {
          var place = angular.copy(data.place);
          place.type = data.place.type.id;
          $ctrl.place = angular.copy(place);
          $ctrl.topography = angular.copy(data.place.topography);
          $ctrl.typeDisabled = angular.copy(data.placeTypeDisabled);
        } else {
          $ctrl.resetPlace();
        }
        $ctrl.loadForm();
      });
    };

    $ctrl.loadForm = function() {
      $ctrl.topographyFields = [
        {
          type: 'input',
          key: 'name',
          templateOptions: {
            label: $translate.instant('NAME'),
            required: true,
          },
        },
        {
          type: 'textarea',
          key: 'alt_name',
          templateOptions: {
            label: $translate.instant('ACCESS.ALT_NAME'),
            rows: 2,
          },
        },
        {
          type: 'input',
          key: 'type',
          templateOptions: {
            label: $translate.instant('TYPE'),
            required: true,
          },
        },
        {
          type: 'textarea',
          key: 'main_category',
          templateOptions: {
            label: $translate.instant('ACCESS.MAIN_CATEGORY'),
            rows: 2,
          },
        },
        {
          type: 'textarea',
          key: 'sub_category',
          templateOptions: {
            label: $translate.instant('ACCESS.SUB_CATEGORY'),
            rows: 2,
          },
        },
        {
          type: 'textarea',
          key: 'reference_code',
          templateOptions: {
            label: $translate.instant('ACCESS.REFERENCE_CODE'),
            required: true,
            rows: 2,
          },
        },
        {
          type: 'datepicker',
          key: 'start_year',
          templateOptions: {
            label: $translate.instant('ACCESS.START_YEAR'),
            appendToBody: false,
            dateFormat: 'YYYY-MM-DD',
            minView: 'year',
          },
        },
        {
          type: 'datepicker',
          key: 'end_year',
          templateOptions: {
            label: $translate.instant('ACCESS.END_YEAR'),
            appendToBody: false,
            dateFormat: 'YYYY-MM-DD',
            minView: 'year',
          },
        },
        {
          type: 'input',
          key: 'lng',
          validators: {
            coordinate: {
              expression: function(viewValue, modelValue) {
                var value = modelValue || viewValue;
                return (
                  /^-?[0-9]{1,3}[.][0-9]{1,6}$/.test(value) ||
                  value === '' ||
                  angular.isUndefined(value) ||
                  value === null
                );
              },
              message: '("ENTER_VALID_COORDINATE_VALUE" | translate)',
            },
          },
          templateOptions: {
            type: 'number',
            label: $translate.instant('ACCESS.LONGITUDE'),
          },
        },
        {
          type: 'input',
          key: 'lat',
          validators: {
            coordinate: {
              expression: function(viewValue, modelValue) {
                var value = modelValue || viewValue;
                return (
                  /^-?[0-9]{1,3}[.][0-9]{1,6}$/.test(value) ||
                  value === '' ||
                  angular.isUndefined(value) ||
                  value === null
                );
              },
              message: '("ENTER_VALID_COORDINATE_VALUE" | translate)',
            },
          },
          templateOptions: {
            type: 'number',
            label: $translate.instant('ACCESS.LATITUDE'),
          },
        },
      ];
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
          key: 'description',
          type: 'textarea',
          templateOptions: {
            label: $translate.instant('DESCRIPTION'),
            rows: 3,
          },
        },
        {
          className: 'row m-0',
          fieldGroup: [
            {
              className: 'col-xs-12 col-sm-6 px-0 pr-md-base',
              type: 'datepicker',
              key: 'start_date',
              templateOptions: {
                label: $translate.instant('START_DATE'),
                appendToBody: false,
                dateFormat: 'YYYY-MM-DD',
              },
            },
            {
              className: 'col-xs-12 col-sm-6 px-0 pl-md-base',
              type: 'datepicker',
              key: 'end_date',
              templateOptions: {
                label: $translate.instant('END_DATE'),
                appendToBody: false,
                dateFormat: 'YYYY-MM-DD',
              },
            },
          ],
        },
      ];
    };

    $ctrl.add = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.adding = true;
      var places = angular.copy(data.agent.places);
      places.forEach(function(x) {
        x.type = x.type.id;
      });
      $ctrl.place.topography = angular.copy($ctrl.topography);
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'agents/' + data.agent.id + '/',
        method: 'PATCH',
        data: {places: [$ctrl.place].concat(places)},
      })
        .then(function(response) {
          $ctrl.adding = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          if (response.data.places) {
            if (angular.isArray($ctrl.nonFieldErrors)) {
              $ctrl.nonFieldErrors = $ctrl.nonFieldErrors.concat(response.data.places);
            } else {
              $ctrl.nonFieldErrors = response.data.places;
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
      var places = angular.copy(data.agent.places);
      places.forEach(function(x, idx, array) {
        if (typeof x.type === 'object') {
          x.type = x.type.id;
        }
        if (x.id === $ctrl.place.id) {
          array[idx] = $ctrl.place;
        }
      });
      $ctrl.place.topography = angular.copy($ctrl.topography);
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'agents/' + data.agent.id + '/',
        method: 'PATCH',
        data: {places: places},
      })
        .then(function(response) {
          $ctrl.saving = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          if (response.data.places) {
            if (angular.isArray($ctrl.nonFieldErrors)) {
              $ctrl.nonFieldErrors = $ctrl.nonFieldErrors.concat(response.data.places);
            } else {
              $ctrl.nonFieldErrors = response.data.places;
            }
          }
          $ctrl.saving = false;
        });
    };

    $ctrl.remove = function() {
      $ctrl.removing = true;
      var toRemove = null;
      var places = angular.copy(data.agent.places);
      places.forEach(function(x, idx, array) {
        if (typeof x.type === 'object') {
          x.type = x.type.id;
        }
        if (x.id === $ctrl.place.id) {
          toRemove = idx;
        }
      });
      if (toRemove !== null) {
        places.splice(toRemove, 1);
      }
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'agents/' + data.agent.id + '/',
        method: 'PATCH',
        data: {places: places},
      })
        .then(function(response) {
          $ctrl.removing = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          if (response.data.places) {
            if (angular.isArray($ctrl.nonFieldErrors)) {
              $ctrl.nonFieldErrors = $ctrl.nonFieldErrors.concat(response.data.places);
            } else {
              $ctrl.nonFieldErrors = response.data.places;
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
  });
