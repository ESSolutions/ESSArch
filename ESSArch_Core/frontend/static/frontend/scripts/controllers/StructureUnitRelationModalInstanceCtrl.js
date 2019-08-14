angular
  .module('essarch.controllers')
  .controller('StructureUnitRelationModalInstanceCtrl', function(
    $uibModalInstance,
    appConfig,
    data,
    $http,
    EditMode,
    $translate,
    $scope,
    $rootScope,
    $filter,
    StructureName
  ) {
    var $ctrl = this;
    $ctrl.data = data;
    $ctrl.isTemplate = true;
    $ctrl.isTemplateOptions = [
      {
        label: $translate.instant('ACCESS.TEMPLATE'),
        value: true,
      },
      {
        label: $translate.instant('ACCESS.INSTANCE'),
        value: false,
      },
    ];

    $ctrl.relation = {
      description: '',
      start_date: null,
      end_date: null,
      create_date: new Date(),
      revise_date: null,
      structure_unit: null,
    };
    $ctrl.structure = {
      value: null,
      options: [],
    };
    $ctrl.unit = {
      value: null,
      options: [],
    };
    $ctrl.options = {};
    $ctrl.initStructureSearch = null;
    $ctrl.initUnitSearch = null;

    $ctrl.getStructures = function(search) {
      return $http({
        url: appConfig.djangoUrl + 'structures/',
        method: 'GET',
        params: {search: search, page: 1, page_size: 10, is_template: $ctrl.isTemplate},
      }).then(function(response) {
        StructureName.parseStructureNames(response.data);
        $ctrl.structure.options = response.data;
        return response.data;
      });
    };

    $ctrl.getStructureUnits = function(search, structure) {
      return $http({
        url: appConfig.djangoUrl + 'structure-units/',
        method: 'GET',
        params: {structure: structure, search: search, page: 1, page_size: 10},
      }).then(function(response) {
        if (angular.isUndefined(structure) || structure === null) {
          $ctrl.unit.options = [];
        } else {
          $ctrl.unit.options = response.data;
        }
        return response.data;
      });
    };

    $ctrl.$onInit = function() {
      $ctrl.data = data;
      if (data.node) {
        $ctrl.node = angular.copy(data.node);
      }
      if (data.relation) {
        $ctrl.relation = angular.copy(data.relation);
        $ctrl.relation.type = angular.copy(data.relation.type.id);
        $ctrl.relation.structure_unit = angular.copy(data.relation.structure_unit.id);
        $ctrl.structure.value = angular.copy(data.relation.structure_unit.structure.id);
        $ctrl.initStructureSearch = data.relation.structure_unit.structure.name;
        $ctrl.initUnitSearch = data.relation.structure_unit.name;
        $ctrl.isTemplate = data.relation.structure_unit.structure.is_template;
      }
      return $http({
        url: appConfig.djangoUrl + 'node-relation-types/',
        method: 'GET',
      }).then(function(response) {
        $ctrl.options.type = response.data;
        $ctrl.buildStructureForm();
        $ctrl.buildForm();
        EditMode.enable();
        return response.data;
      });
    };

    $ctrl.buildStructureForm = function() {
      $ctrl.structureFields = [
        {
          type: 'uiselect',
          key: 'value',
          templateOptions: {
            required: true,
            options: function() {
              return $ctrl.structure.options;
            },
            valueProp: 'id',
            labelProp: 'name_with_version',
            placeholder: $translate.instant('ACCESS.CLASSIFICATION_STRUCTURE'),
            label: $translate.instant('ACCESS.CLASSIFICATION_STRUCTURE'),
            clearEnabled: true,
            appendToBody: false,
            refresh: function(search) {
              if ($ctrl.initStructureSearch && (angular.isUndefined(search) || search === null || search === '')) {
                search = angular.copy($ctrl.initStructureSearch);
                $ctrl.initStructureSearch = null;
              }
              $ctrl.getStructures(search).then(function() {
                this.options = $ctrl.structure.options;
              });
            },
          },
        },
      ];
    };

    $ctrl.buildForm = function() {
      $ctrl.fields = [
        {
          type: 'uiselect',
          key: 'structure_unit',
          templateOptions: {
            required: true,
            options: function() {
              return $ctrl.unit.options;
            },
            valueProp: 'id',
            labelProp: 'name',
            required: true,
            placeholder: $translate.instant('ACCESS.STRUCTURE_UNIT'),
            label: $translate.instant('ACCESS.STRUCTURE_UNIT'),
            appendToBody: false,
            clearEnabled: true,
            refresh: function(search) {
              if ($ctrl.initUnitSearch && (angular.isUndefined(search) || search === null || search === '')) {
                search = angular.copy($ctrl.initUnitSearch);
                $ctrl.initUnitSearch = null;
              }
              $ctrl.getStructureUnits(search, $ctrl.structure.value).then(function() {
                this.options = $ctrl.unit.options;
              });
            },
          },
        },
        {
          key: 'type',
          type: 'select',
          templateOptions: {
            options: $ctrl.options.type,
            label: $translate.instant('TYPE'),
            labelProp: 'name',
            valueProp: 'id',
            notNull: true,
            required: true,
          },
          defaultValue: $ctrl.options.type.length > 0 ? $ctrl.options.type[0].id : null,
        },
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
          key: 'description',
          type: 'textarea',
          templateOptions: {
            label: $translate.instant('DESCRIPTION'),
            rows: 3,
          },
        },
      ];
    };

    $ctrl.add = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      var units = angular.copy($ctrl.node).related_structure_units.map(function(x) {
        x.structure_unit = angular.copy(x.structure_unit.id);
        x.type = angular.copy(x.type.id);
        return x;
      });
      $ctrl.adding = true;
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'structure-units/' + $ctrl.node.id + '/',
        method: 'PATCH',
        data: {
          related_structure_units: units.concat([$ctrl.relation]),
        },
      })
        .then(function(response) {
          $ctrl.adding = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.adding = false;
          EditMode.disable();
        });
    };

    $ctrl.save = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      var units = angular.copy($ctrl.node).related_structure_units;
      units.forEach(function(x, idx, array) {
        x.structure_unit = angular.copy(x.structure_unit.id);
        x.type = angular.copy(x.type.id);
        if (x.id === $ctrl.relation.id) {
          array[idx] = $ctrl.relation;
        }
      });
      $ctrl.saving = true;
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'structure-units/' + $ctrl.node.id + '/',
        method: 'PATCH',
        data: {
          related_structure_units: units,
        },
      })
        .then(function(response) {
          $ctrl.saving = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.saving = false;
          EditMode.disable();
        });
    };

    $ctrl.remove = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      var toRemove = null;
      var units = angular.copy($ctrl.node).related_structure_units;
      units.forEach(function(x, idx) {
        x.structure_unit = angular.copy(x.structure_unit.id);
        x.type = angular.copy(x.type.id);
        if (x.id === $ctrl.relation.id) {
          toRemove = idx;
        }
      });
      if (toRemove !== null) {
        units.splice(toRemove, 1);
      }
      $ctrl.removing = true;
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'structure-units/' + $ctrl.node.id + '/',
        method: 'PATCH',
        data: {
          related_structure_units: units,
        },
      })
        .then(function(response) {
          $ctrl.removing = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.removing = false;
          EditMode.disable();
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
