export default class AgentNameModalInstanceCtrl {
  constructor($uibModalInstance, $scope, $translate, $http, appConfig, data, EditMode, $rootScope) {
    const $ctrl = this;
    $ctrl.name;
    $ctrl.nameTemplate = {
      part: '',
      main: '',
      description: '',
      start_date: null,
      end_date: null,
      type: null,
      certainty: null,
    };
    $ctrl.fields = [];
    $ctrl.resetName = function() {
      $ctrl.name = angular.copy($ctrl.nameTemplate);
    };

    $ctrl.$onInit = function() {
      return $http({
        url: appConfig.djangoUrl + 'agent-name-types/',
        params: {pager: 'none'},
        method: 'GET',
      }).then(function(response) {
        $ctrl.options = {type: response.data};
        EditMode.enable();
        if (data.name) {
          const name = angular.copy(data.name);
          name.type = data.name.type.id;
          $ctrl.name = angular.copy(name);
          $ctrl.typeDisabled = angular.copy(data.nameTypeDisabled);
        } else {
          $ctrl.resetName();
        }
        $ctrl.loadForm();
      });
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
            disabled: $ctrl.typeDisabled,
            labelProp: 'name',
            valueProp: 'id',
            defaultValue: $ctrl.options.type[0].id,
            notNull: true,
          },
        },
      ];
      if (data.agent.type && data.agent.type.cpf && data.agent.type.cpf !== 'corporatebody') {
        $ctrl.fields.push({
          className: 'row m-0',
          fieldGroup: [
            {
              className: 'col-xs-12 col-sm-6 px-0 pr-md-base',
              type: 'input',
              key: 'part',
              templateOptions: {
                label: $translate.instant('ACCESS.PART'),
              },
            },
            {
              className: 'col-xs-12 col-sm-6 px-0 pl-md-base',
              type: 'input',
              key: 'main',
              templateOptions: {
                label: $translate.instant('ACCESS.MAIN'),
                required: true,
              },
            },
          ],
        });
      } else {
        $ctrl.fields.push({
          type: 'input',
          key: 'main',
          templateOptions: {
            label: $translate.instant('NAME'),
            required: true,
          },
        });
      }
      $ctrl.fields = $ctrl.fields.concat([
        {
          className: 'row m-0',
          fieldGroup: [
            {
              className: 'col-xs-12 col-sm-6 px-0 pr-md-base',
              type: 'datepicker',
              key: 'start_date',
              templateOptions: {
                label: $translate.instant('ACCESS.VALID_DATE_START'),
                appendToBody: false,
                dateFormat: 'YYYY-MM-DD',
              },
            },
            {
              className: 'col-xs-12 col-sm-6 px-0 pl-md-base',
              type: 'datepicker',
              key: 'end_date',
              templateOptions: {
                label: $translate.instant('ACCESS.VALID_DATE_END'),
                appendToBody: false,
                dateFormat: 'YYYY-MM-DD',
              },
            },
          ],
        },
        {
          type: 'select',
          key: 'certainty',
          templateOptions: {
            options: [
              {value: true, display_name: $translate.instant('ACCESS.SURE')},
              {value: false, display_name: $translate.instant('ACCESS.UNSURE')},
            ],
            valueProp: 'value',
            labelProp: 'display_name',
            label: $translate.instant('ACCESS.CERTAINTY'),
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
      ]);
    };

    $ctrl.add = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.adding = true;
      const names = angular.copy(data.agent.names);
      names.forEach(function(x) {
        x.type = x.type.id;
      });
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'agents/' + data.agent.id + '/',
        method: 'PATCH',
        data: {names: [$ctrl.name].concat(names)},
      })
        .then(function(response) {
          $ctrl.adding = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          if (response.data.names) {
            if (angular.isArray($ctrl.nonFieldErrors)) {
              $ctrl.nonFieldErrors = $ctrl.nonFieldErrors.concat(response.data.names);
            } else {
              $ctrl.nonFieldErrors = response.data.names;
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
      const names = angular.copy(data.agent.names);
      names.forEach(function(x, idx, array) {
        if (typeof x.type === 'object') {
          x.type = x.type.id;
        }
        if (x.id === $ctrl.name.id) {
          array[idx] = $ctrl.name;
        }
      });
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'agents/' + data.agent.id + '/',
        method: 'PATCH',
        data: {names: names},
      })
        .then(function(response) {
          $ctrl.saving = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          if (response.data.names) {
            if (angular.isArray($ctrl.nonFieldErrors)) {
              $ctrl.nonFieldErrors = $ctrl.nonFieldErrors.concat(response.data.names);
            } else {
              $ctrl.nonFieldErrors = response.data.names;
            }
          }
          $ctrl.saving = false;
        });
    };

    $ctrl.remove = function() {
      $ctrl.removing = true;
      let toRemove = null;
      const names = angular.copy(data.agent.names);
      names.forEach(function(x, idx, array) {
        if (typeof x.type === 'object') {
          x.type = x.type.id;
        }
        if (x.id === $ctrl.name.id) {
          toRemove = idx;
        }
      });
      if (toRemove !== null) {
        names.splice(toRemove, 1);
      }
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'agents/' + data.agent.id + '/',
        method: 'PATCH',
        data: {names: names},
      })
        .then(function(response) {
          $ctrl.removing = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          if (response.data.names) {
            if (angular.isArray($ctrl.nonFieldErrors)) {
              $ctrl.nonFieldErrors = $ctrl.nonFieldErrors.concat(response.data.names);
            } else {
              $ctrl.nonFieldErrors = response.data.names;
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
