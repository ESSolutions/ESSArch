export default class PlaceNodeInArchiveModalInstanceCtrl {
  constructor($uibModalInstance, $scope, $translate, $http, appConfig, data, EditMode, StructureName) {
    const $ctrl = this;
    $ctrl.archiveFields = [];
    $ctrl.structureFields = [];
    $ctrl.model = {};

    $ctrl.archiveModel = {archive: null};
    $ctrl.structureModel = {structure: null};
    $ctrl.options = {
      structure: [],
      archive: [],
      unit: [],
      node: [],
    };

    $ctrl.getArchives = function(search) {
      return $http({
        url: appConfig.djangoUrl + 'tags/',
        mathod: 'GET',
        params: {page: 1, page_size: 10, index: 'archive', search: search},
      }).then(function(response) {
        $ctrl.options.archive = response.data.map(function(x) {
          x.current_version.name_with_dates =
            x.current_version.name +
            (x.current_version.start_date !== null || x.current_version.end_date != null
              ? ' (' +
                (x.current_version.start_date !== null ? $filter('date')(x.current_version.start_date, 'yyyy') : '') +
                ' - ' +
                (x.current_version.end_date !== null ? $filter('date')(x.current_version.end_date, 'yyyy') : '') +
                ')'
              : '');
          return x.current_version;
        });
        return $ctrl.options.archive;
      });
    };

    $ctrl.getStructures = function(search, archive) {
      return $http({
        url: appConfig.djangoUrl + 'structures/',
        method: 'GET',
        params: {search: search, archive: archive, page: 1, page_size: 10, is_template: $ctrl.isTemplate},
      }).then(function(response) {
        StructureName.parseStructureNames(response.data);
        $ctrl.options.structure = response.data;
        return response.data;
      });
    };

    $ctrl.getStructureUnits = function(search, structure, archive) {
      return $http({
        url: appConfig.djangoUrl + 'structure-units/',
        method: 'GET',
        params: {structure, archive, template: false, search: search, page: 1, page_size: 10},
      }).then(function(response) {
        if (angular.isUndefined(structure) || structure === null) {
          $ctrl.options.unit = [];
        } else {
          $ctrl.options.unit = response.data;
        }
        return response.data;
      });
    };

    $ctrl.getNodes = function(search, structureUnit, structure, archive) {
      let url;
      if (structureUnit) {
        url = appConfig.djangoUrl + 'structure-units/' + structureUnit + '/children/';
      } else {
        url = appConfig.djangoUrl + 'tags/';
      }
      return $http({
        url,
        method: 'GET',
        params: {structure, search, archive, page: 1, page_size: 10},
      }).then(function(response) {
        let nodes = [];
        if (!structureUnit) {
          nodes = response.data.map(x => {
            x.current_version._id = x.current_version.id;
            return x.current_version;
          });
        } else {
          nodes = response.data;
        }
        if (angular.isUndefined(structure) || structure === null) {
          $ctrl.options.node = [];
        } else {
          $ctrl.options.node = nodes;
        }
        return nodes;
      });
    };

    $ctrl.$onInit = function() {
      $ctrl.data = data;
      if (data.node) {
        $ctrl.node = angular.copy(data.node);
      }
      $ctrl.buildStructureForm();
      $ctrl.buildForm();
    };

    $ctrl.buildStructureForm = function() {
      $ctrl.archiveFields = [
        {
          type: 'uiselect',
          key: 'archive',
          templateOptions: {
            required: true,
            options: function() {
              return $ctrl.options.archive;
            },
            valueProp: 'id',
            labelProp: 'name_with_dates',
            placeholder: $translate.instant('ACCESS.ARCHIVE'),
            label: $translate.instant('ACCESS.ARCHIVE'),
            clearEnabled: true,
            appendToBody: false,
            optionsFunction: function(search) {
              return $ctrl.options.archive;
            },
            refresh: function(search) {
              if ($ctrl.initArchiveSearch && (angular.isUndefined(search) || search === null || search === '')) {
                search = angular.copy($ctrl.initArchiveSearch);
                $ctrl.initArchiveSearch = null;
              }
              return $ctrl.getArchives(search).then(function() {
                this.options = $ctrl.options.archive;
                return $ctrl.options.archive;
              });
            },
          },
          expressionProperties: {
            'templateOptions.onChange': function($modelValue) {
              $ctrl.structureModel.structure = null;
              $ctrl.relation.structure_unit = null;
            },
          },
        },
      ];
      $ctrl.structureFields = [
        {
          type: 'uiselect',
          key: 'structure',
          templateOptions: {
            required: true,
            options: function() {
              return $ctrl.options.structure;
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
              return $ctrl.getStructures(search, $ctrl.archiveModel.archive).then(function() {
                this.options = $ctrl.options.structure;
                return $ctrl.options.structure;
              });
            },
          },
          expressionProperties: {
            'templateOptions.onChange': function($modelValue) {
              $ctrl.relation.structure_unit = null;
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
              return $ctrl.options.unit;
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
              return $ctrl
                .getStructureUnits(search, $ctrl.structureModel.structure, $ctrl.archiveModel.archive)
                .then(function() {
                  this.options = $ctrl.options.unit;
                  return $ctrl.options.unit;
                });
            },
          },
        },
        {
          type: 'uiselect',
          key: 'node',
          templateOptions: {
            options: function() {
              return $ctrl.options.node;
            },
            valueProp: '_id',
            labelProp: 'name',
            placeholder: $translate.instant('ACCESS.NODE'),
            label: $translate.instant('ACCESS.NODE'),
            appendToBody: false,
            clearEnabled: true,
            refresh: function(search) {
              if ($ctrl.initUnitSearch && (angular.isUndefined(search) || search === null || search === '')) {
                search = angular.copy($ctrl.initNodeSearch);
                $ctrl.initNodeSearch = null;
              }
              return $ctrl
                .getNodes(
                  search,
                  $ctrl.model.structure_unit,
                  $ctrl.structureModel.structure,
                  $ctrl.archiveModel.archive
                )
                .then(function() {
                  this.options = $ctrl.options.node;
                  return $ctrl.options.node;
                });
            },
          },
        },
      ];
    };

    $ctrl.place = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      let patchData = {
        index: data.node._index,
        structure: $ctrl.structureModel.structure,
        archive: $ctrl.archiveModel.archive,
      };
      if ($ctrl.model.node) {
        patchData.parent = $ctrl.model.node;
      } else if ($ctrl.model.structure_unit) {
        patchData.structure_unit = $ctrl.model.structure_unit;
        patchData.parent = $ctrl.archiveModel.archive;
      }
      $ctrl.placing = true;
      $http({
        url: appConfig.djangoUrl + 'search/' + data.node._id + '/',
        method: 'PATCH',
        data: patchData,
      })
        .then(function(response) {
          $ctrl.placing = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.placing = false;
          $ctrl.nonFieldErrors = response.data.non_field_errors;
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
