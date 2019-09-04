export default class EditStructureUnitModalInstanceCtrl {
  constructor($translate, $uibModalInstance, appConfig, $http, data, $scope, Notifications, EditMode, $rootScope) {
    const $ctrl = this;
    $ctrl.editNode = {};
    $ctrl.options = {};
    $ctrl.nodeFields = [];
    $ctrl.types = [];
    $ctrl.$onInit = function() {
      if (data.node) {
        $ctrl.node = data.node;
        EditMode.enable();
        $ctrl.editNode = angular.copy($ctrl.node);
        $ctrl.editNode.type = $ctrl.node.type.id;
        if ($ctrl.editNode.related_structure_units) {
          delete $ctrl.editNode.related_structure_units;
        }
      }
      if (data.structure) {
        $ctrl.structure = data.structure;
      }
      $http
        .get(appConfig.djangoUrl + 'structure-unit-types/', {
          params: {structure_type: data.structure.structureType.id, pager: 'none'},
        })
        .then(function(response) {
          $ctrl.structureUnitTypes = response.data;
          $ctrl.buildNodeForm();
        });
    };

    $ctrl.buildNodeForm = function() {
      $ctrl.nodeFields = [
        {
          templateOptions: {
            label: $translate.instant('ACCESS.REFERENCE_CODE'),
            focus: true,
            required: true,
          },
          type: 'input',
          key: 'reference_code',
        },
        {
          templateOptions: {
            type: 'text',
            label: $translate.instant('NAME'),
          },
          type: 'input',
          key: 'name',
        },
        {
          type: 'select',
          key: 'type',
          templateOptions: {
            valueProp: 'id',
            labelProp: 'name',
            label: $translate.instant('TYPE'),
            options: $ctrl.structureUnitTypes,
            required: true,
            notNull: true,
          },
          defaultValue: $ctrl.structureUnitTypes.length > 0 ? $ctrl.structureUnitTypes[0].id : null,
        },
        {
          templateOptions: {
            label: $translate.instant('DESCRIPTION'),
            rows: 3,
          },
          type: 'textarea',
          key: 'description',
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
              },
            },
            {
              className: 'col-xs-12 col-sm-6 px-0 pl-md-base',
              type: 'datepicker',
              key: 'end_date',
              templateOptions: {
                label: $translate.instant('END_DATE'),
                appendToBody: false,
              },
            },
          ],
        },
      ];
    };

    $ctrl.changed = function() {
      return !angular.equals($ctrl.editNode, $ctrl.node);
    };
    /**
     * update new classification structure
     */
    $ctrl.saving = false;
    $ctrl.update = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.saving = true;
      $rootScope.skipErrorNotification = true;
      $http({
        method: 'PATCH',
        url: appConfig.djangoUrl + 'structures/' + data.structure.id + '/units/' + $ctrl.node.id + '/',
        data: $ctrl.editNode,
      })
        .then(function(response) {
          $ctrl.saving = false;
          Notifications.add($translate.instant('ACCESS.NODE_EDITED'), 'success');
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.saving = false;
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
