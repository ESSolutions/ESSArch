export default class EditNodeModalInstanceCtrl {
  constructor(
    Search,
    $translate,
    $uibModalInstance,
    $scope,
    appConfig,
    $http,
    data,
    Notifications,
    EditMode,
    $rootScope
  ) {
    const $ctrl = this;
    $ctrl.node = data.node;
    $ctrl.editData = {};
    $ctrl.editFields = [];
    $ctrl.editFieldsNoDelete = [];
    $ctrl.options = {};
    $ctrl.fieldOptions = {};
    $ctrl.newFieldKey = null;
    $ctrl.newFieldVal = null;
    $ctrl.updateDescendants = false;
    $ctrl.manyNodes = false;
    $ctrl.options = {};
    $ctrl.customFields = [];
    $ctrl.$onInit = function() {
      $http
        .get(appConfig.djangoUrl + 'tag-version-types/', {
          params: {archive_type: data.node && data.node._index === 'archive', pager: 'none'},
        })
        .then(function(response) {
          $ctrl.options.type = response.data;
          $ctrl.node = angular.copy(data.node);
          $ctrl.node.type = data.node.type.pk;
          $ctrl.loadForm();
          EditMode.enable();
        });
    };

    function deleteField(field) {
      $ctrl.customFields.forEach(function(x, idx, array) {
        if (x.key === field) {
          array.splice(idx, 1);
          delete $ctrl.node.custom_fields[field];
        }
      });
    }

    function clearObject(obj) {
      angular.forEach(obj, function(val, key) {
        obj[key] = null;
      });
    }

    $ctrl.selected = null;

    $ctrl.changed = function() {
      return !angular.equals($ctrl.node, data.node);
    };

    $ctrl.addNewField = function() {
      if ($ctrl.newFieldKey && $ctrl.newFieldVal) {
        const newFieldKey = angular.copy($ctrl.newFieldKey);
        const newFieldVal = angular.copy($ctrl.newFieldVal);
        const splitted = newFieldKey.split('.');
        if (
          (splitted.length > 1 && !angular.isUndefined($ctrl.node.custom_fields[splitted[0]][splitted[1]])) ||
          !angular.isUndefined($ctrl.node.custom_fields[newFieldKey])
        ) {
          Notifications.add($translate.instant('ACCESS.FIELD_EXISTS'), 'error');
          return;
        }
        if (splitted.length > 1) {
          $ctrl.node.custom_fields[splitted[0]][splitted[1]] = newFieldVal;
        } else {
          $ctrl.node.custom_fields[newFieldKey] = newFieldVal;
        }
        $ctrl.customFields.push({
          templateOptions: {
            type: 'text',
            label: newFieldKey,
            delete: function() {
              deleteField(newFieldKey);
            },
          },
          type: 'input',
          key: newFieldKey,
        });
        $ctrl.newFieldKey = null;
        $ctrl.newFieldVal = null;
      }
    };

    function getEditedFields(node) {
      const edited = {};
      const oldModel = angular.copy(data.node);
      oldModel.type = oldModel.type.pk;
      angular.forEach(node, function(value, key) {
        if (oldModel[key] !== value && typeof value !== 'object' && !angular.isArray(value)) {
          edited[key] = value;
        }
      });
      if (!angular.isUndefined(node.custom_fields)) {
        edited.custom_fields = node.custom_fields;
      }
      return edited;
    }

    $ctrl.editField = function(field, value) {
      $ctrl.node[field] = value;
      $ctrl.fields.push({
        templateOptions: {
          type: 'text',
          label: field,
        },
        type: 'input',
        key: field,
      });
    };

    $ctrl.loadForm = function() {
      $ctrl.fields = [
        {
          key: 'name',
          type: 'input',
          templateOptions: {
            label: $translate.instant('NAME'),
            required: true,
          },
        },
        {
          key: 'type',
          type: 'select',
          templateOptions: {
            label: $translate.instant('TYPE'),
            required: true,
            options: $ctrl.options.type,
            valueProp: 'pk',
            labelProp: 'name',
            notNull: true,
          },
          defaultValue: $ctrl.options.type.length > 0 ? $ctrl.options.type[0].pk : null,
        },
        {
          key: 'reference_code',
          type: 'input',
          templateOptions: {
            label: $translate.instant('ACCESS.REFERENCE_CODE'),
            required: true,
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
      $ctrl.customFields = [];
      angular.forEach($ctrl.node.custom_fields, function(value, key) {
        $ctrl.customFields.push({
          key: key,
          type: 'input',
          templateOptions: {
            label: key,
            delete: function() {
              deleteField(key);
            },
          },
        });
      });
    };

    $ctrl.updateSingleNode = function() {
      $rootScope.skipErrorNotification = true;
      Search.updateNode($ctrl.node, getEditedFields($ctrl.node))
        .then(function(response) {
          $ctrl.submitting = false;
          Notifications.add($translate.instant('ACCESS.NODE_EDITED'), 'success');
          EditMode.disable();
          $uibModalInstance.close('edited');
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.submitting = false;
        });
    };

    $ctrl.updateNodeAndDescendants = function() {
      if ($ctrl.changed()) {
        $rootScope.skipErrorNotification = true;
        Search.updateNodeAndDescendants($ctrl.node, getEditedFields($ctrl.node))
          .then(function(response) {
            $ctrl.submitting = false;
            Notifications.add($translate.instant('ACCESS.NODE_EDITED'), 'success');
            EditMode.disable();
            $uibModalInstance.close('edited');
          })
          .catch(function(response) {
            $ctrl.nonFieldErrors = response.data.non_field_errors;
            $ctrl.submitting = false;
          });
      }
    };

    $ctrl.massUpdate = function() {
      if ($ctrl.changed()) {
        $rootScope.skipErrorNotification = true;
        Search.massUpdate($ctrl.nodeList, getEditedFields($ctrl.node))
          .then(function(response) {
            $ctrl.submitting = false;
            Notifications.add($translate.instant('ACCESS.NODE_EDITED'), 'success');
            EditMode.disable();
            $uibModalInstance.close('edited');
          })
          .catch(function(response) {
            $ctrl.nonFieldErrors = response.data.non_field_errors;
            $ctrl.submitting = false;
          });
      }
    };

    $ctrl.submit = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      if ($ctrl.manyNodes) {
        $ctrl.massUpdate();
      } else if ($ctrl.updateDescendants) {
        $ctrl.updateNodeAndDescendants();
      } else {
        $ctrl.updateSingleNode();
      }
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
