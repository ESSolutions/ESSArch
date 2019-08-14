angular
  .module('essarch.controllers')
  .controller('AgentModalInstanceCtrl', function(
    $uibModalInstance,
    data,
    appConfig,
    $http,
    $scope,
    EditMode,
    $translate,
    $rootScope,
    $q
  ) {
    var $ctrl = this;
    $ctrl.options = {};
    $ctrl.authName = {
      part: '',
      main: '',
      description: '',
      start_date: null,
      end_date: null,
      type: 1,
      certainty: null,
    };
    $ctrl.nameFields = [];
    $ctrl.basicFields = [];

    $ctrl.buildAgentModel = function() {
      return $http({
        url: appConfig.djangoUrl + 'agents/',
        method: 'OPTIONS',
      }).then(function(response) {
        var model = {};
        angular.forEach(response.data.actions.POST, function(value, key) {
          if (value.many) {
            model[key] = [];
          } else if (value.type === 'datetime') {
            model[key] = new Date();
          } else {
            model[key] = null;
          }
          if (!angular.isUndefined(value.choices) && value.choices.length > 0) {
            $ctrl.options[key] = value;
            model[key] = value.choices[0].value;
          }
          if (!angular.isUndefined(value.child) && !angular.isUndefined(value.child.children)) {
            angular.forEach(value.child.children, function(nestedVal, nestedKey) {
              if (!angular.isUndefined(nestedVal.choices)) {
                $ctrl.options[key] = {
                  child: {
                    children: {},
                  },
                };
                $ctrl.options[key].child.children[nestedKey] = nestedVal;
              }
            });
          }
        });
        delete model.id;
        model.identifiers = [];
        model.mandates = [];
        model.related_agents = [];
        model.notes = [];
        model.places = [];
        return model;
      });
    };

    $ctrl.$onInit = function() {
      if (data.remove && data.agent) {
        $ctrl.agent = angular.copy(data.agent);
        return;
      }
      if (data.agent) {
        return $http({
          url: appConfig.djangoUrl + 'agents/',
          method: 'OPTIONS',
        }).then(function(response) {
          $ctrl.agent = angular.copy(data.agent);
          $ctrl.agent.ref_code = data.agent.ref_code.id;
          angular.forEach(response.data.actions.POST, function(value, key) {
            if (!angular.isUndefined(value.choices) && value.choices.length > 0) {
              $ctrl.options[key] = value;
            }
            if (!angular.isUndefined(value.child) && !angular.isUndefined(value.child.children)) {
              angular.forEach(value.child.children, function(nestedVal, nestedKey) {
                if (!angular.isUndefined(nestedVal.choices)) {
                  $ctrl.options[key] = {
                    child: {
                      children: {},
                    },
                  };
                  $ctrl.options[key].child.children[nestedKey] = nestedVal;
                }
              });
            }
          });
          $ctrl.buildTypeField($ctrl.agent).then(function(typeField) {
            $ctrl.loadBasicFields();
            $ctrl.basicFields.unshift(typeField);
          });
        });
      } else {
        $ctrl.buildAgentModel().then(function(model) {
          $ctrl.agent = model;
          $ctrl.buildTypeField($ctrl.agent).then(function(typeField) {
            typeField.templateOptions.onChange = function($modelValue) {
              if ($modelValue && $modelValue.cpf && $modelValue.cpf === 'corporatebody') {
                $ctrl.authName.part = '';
              }
              $ctrl.loadForms();
            };
            $ctrl.typeField = [typeField];
          });
        });
      }
      EditMode.enable();
    };

    $ctrl.buildTypeField = function(agent) {
      return $http.get(appConfig.djangoUrl + 'agent-types/', {params: {pager: 'none'}}).then(function(response) {
        var options = angular.copy(response.data);
        options.forEach(function(x) {
          x.name = x.main_type.name;
        });
        var type = {
          type: 'select',
          key: 'type',
          templateOptions: {
            options: options,
            getTypeName: function(type) {
              return (
                type.main_type.name +
                (type.sub_type !== null && type.sub_type !== '' ? ' (' + type.sub_type + ')' : '')
              );
            },
            ngOptions: 'to.getTypeName(x) for x in to.options',
            label: $translate.instant('TYPE'),
            required: true,
            notNull: true,
          },
        };
        return type;
      });
    };

    $ctrl.loadForms = function() {
      $ctrl.nameFields = [];
      $ctrl.basicFields = [];
      $ctrl.loadNameForm();
      $ctrl.loadBasicFields();
    };

    $ctrl.loadNameForm = function() {
      $ctrl.nameFields = [];
      if ($ctrl.agent.type && $ctrl.agent.type.cpf && $ctrl.agent.type.cpf !== 'corporatebody') {
        $ctrl.nameFields.push({
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
        $ctrl.nameFields.push({
          type: 'input',
          key: 'main',
          templateOptions: {
            label: $translate.instant('NAME'),
            required: true,
          },
        });
      }

      $ctrl.nameFields = $ctrl.nameFields.concat([
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
              expressionProperties: {
                'templateOptions.onChange': function($modelValue) {
                  if (
                    $modelValue &&
                    ($ctrl.agent.start_date === null || angular.isUndefined($ctrl.agent.start_date))
                  ) {
                    $ctrl.agent.start_date = $modelValue;
                  }
                },
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
              expressionProperties: {
                'templateOptions.onChange': function($modelValue) {
                  if ($modelValue && ($ctrl.agent.end_date === null || angular.isUndefined($ctrl.agent.end_date))) {
                    $ctrl.agent.end_date = $modelValue;
                  }
                },
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

    $ctrl.loadBasicFields = function() {
      var promises = [];
      promises.push(
        $ctrl.getRefCodes().then(function(refCodes) {
          if (refCodes.length > 0 && (angular.isUndefined($ctrl.agent.ref_code) || $ctrl.agent.ref_code === null)) {
            $ctrl.agent.ref_code = refCodes[0].id;
          }
          return refCodes;
        })
      );
      promises.push(
        $ctrl.getLanguages().then(function(languages) {
          if (angular.isUndefined($ctrl.agent.language) || $ctrl.agent.language === null) {
            $ctrl.agent.language = 'sv';
          }
          return languages;
        })
      );
      $q.all(promises).then(function(responses) {
        $ctrl.basicFields = [
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
          {
            type: 'select',
            key: 'level_of_detail',
            templateOptions: {
              options: $ctrl.options.level_of_detail.choices,
              valueProp: 'value',
              labelProp: 'display_name',
              label: $translate.instant('ACCESS.LEVEL_OF_DETAIL'),
              defaultValue: $ctrl.options.level_of_detail.choices[0].value,
              required: true,
              notNull: true,
            },
          },
          {
            type: 'uiselect',
            key: 'language',
            templateOptions: {
              options: function() {
                return $ctrl.options.language.choices;
              },
              valueProp: 'id',
              labelProp: 'name_en',
              label: $translate.instant('ACCESS.LANGUAGE'),
              appendToBody: false,
              optionsFunction: function(search) {
                return $ctrl.options.language.choices;
              },
              refresh: function(search) {
                $ctrl.getLanguages(search).then(function() {
                  this.options = $ctrl.options.language.choices;
                });
              },
              defaultValue: $ctrl.options.language.choices.length > 0 ? $ctrl.options.language.choices[0].id : null,
              required: true,
            },
          },
          {
            type: 'select',
            key: 'record_status',
            templateOptions: {
              options: $ctrl.options.record_status.choices,
              valueProp: 'value',
              labelProp: 'display_name',
              label: $translate.instant('ACCESS.RECORD_STATUS'),
              defaultValue: $ctrl.options.record_status.choices[0].value,
              required: true,
              notNull: true,
            },
          },
          {
            type: 'select',
            key: 'ref_code',
            templateOptions: {
              options: $ctrl.options.ref_code.choices,
              valueProp: 'id',
              labelProp: 'formatted_name',
              label: $translate.instant('ACCESS.REFERENCE_CODE'),
              defaultValue: $ctrl.options.ref_code.choices.length > 0 ? $ctrl.options.ref_code.choices[0].id : null,
              required: true,
              notNull: true,
            },
          },
          {
            type: 'datepicker',
            key: 'create_date',
            templateOptions: {
              label: $translate.instant('CREATE_DATE'),
              appendToBody: false,
              required: true,
            },
          },
        ];
      });
    };

    $ctrl.getLanguages = function(search) {
      return $http
        .get(appConfig.djangoUrl + 'languages/', {params: {search: search, pager: 'none'}})
        .then(function(response) {
          $ctrl.options.language = {choices: response.data};
          return response.data;
        });
    };
    $ctrl.getRefCodes = function() {
      return $http.get(appConfig.djangoUrl + 'ref-codes/', {params: {pager: 'none'}}).then(function(response) {
        response.data.forEach(function(x) {
          x.formatted_name = x.country + '/' + x.repository_code;
        });
        $ctrl.options.ref_code = {choices: response.data};
        return response.data;
      });
    };

    $ctrl.cancel = function() {
      EditMode.disable();
      $uibModalInstance.dismiss('cancel');
    };
    $ctrl.create = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.creating = true;
      $ctrl.agent.names = [];
      $ctrl.agent.names.push($ctrl.authName);
      var agent = angular.copy($ctrl.agent);
      agent.type = $ctrl.agent.type.id;
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'agents/',
        method: 'POST',
        data: agent,
      })
        .then(function(response) {
          $ctrl.creating = false;
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
          $ctrl.creating = false;
        });
    };
    $ctrl.save = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      var agent = angular.copy($ctrl.agent);
      agent.type = $ctrl.agent.type.id;
      angular.forEach(agent, function(value, key) {
        if (angular.isArray(value)) {
          delete agent[key];
        }
      });
      $ctrl.saving = true;
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'agents/' + data.agent.id + '/',
        method: 'PATCH',
        data: agent,
      })
        .then(function(response) {
          $ctrl.saving = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function() {
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
      $rootScope.skipErrorNotification = true;
      $http
        .delete(appConfig.djangoUrl + 'agents/' + $ctrl.agent.id)
        .then(function(response) {
          $ctrl.removing = false;
          EditMode.disable();
          $uibModalInstance.close('removed');
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.removing = false;
        });
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
