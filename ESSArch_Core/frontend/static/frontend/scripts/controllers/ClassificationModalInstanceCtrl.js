export default class ClassificationModalInstanceCtrl {
  constructor(
    data,
    $http,
    appConfig,
    Notifications,
    $uibModalInstance,
    $translate,
    Structure,
    EditMode,
    $scope,
    $rootScope
  ) {
    const $ctrl = this;
    $ctrl.name = null;
    $ctrl.newNode = {};
    $ctrl.options = {};
    $ctrl.nodeFields = [];
    $ctrl.structureFields = [];
    $ctrl.types = [];
    $ctrl.data = data;
    $ctrl.newStructure = {};
    $ctrl.$onInit = function() {
      if (data.node) {
        $ctrl.node = data.node;
      }
      EditMode.enable();
      if (data.structure) {
        $http.get(appConfig.djangoUrl + 'structure-types/', {params: {pager: 'none'}}).then(function(response) {
          $ctrl.typeOptions = response.data;
          $ctrl.structure = angular.copy(data.structure);
          $ctrl.structure.type = angular.copy(data.structure.structureType.id);
          $ctrl.buildStructureForm();
        });
      }
      if (data.newStructure) {
        $http.get(appConfig.djangoUrl + 'structure-types/', {params: {pager: 'none'}}).then(function(response) {
          $ctrl.typeOptions = response.data;
          $ctrl.buildStructureForm();
        });
      } else {
        $http
          .get(appConfig.djangoUrl + 'structure-unit-types/', {
            params: {structure_type: data.structure.structureType.id, pager: 'none'},
          })
          .then(function(response) {
            if (data.node.structureType) {
              if (data.children) {
                $ctrl.newNode.reference_code = (data.children.length + 1).toString();
              }
              EditMode.enable();
            } else {
              if (data.node._index !== 'archive') {
                const url = appConfig.djangoUrl + 'structure-units/' + data.node.id + '/children/';
                $http.head(url).then(function(childrenResponse) {
                  const count = parseInt(childrenResponse.headers('Count'));
                  if (!isNaN(count)) {
                    $ctrl.newNode.reference_code = (count + 1).toString();
                  }
                  EditMode.enable();
                });
              }
            }
            $ctrl.structureUnitTypes = response.data;
            $ctrl.buildNodeForm();
          });
      }
    };

    $ctrl.buildStructureForm = function() {
      $ctrl.structureFields = [
        {
          key: 'name',
          type: 'input',
          templateOptions: {
            label: $translate.instant('NAME'),
            required: true,
          },
        },
        {
          className: 'row m-0',
          fieldGroup: [
            {
              className: 'col-xs-12 col-sm-6 px-0 pr-md-base',
              type: 'select',
              key: 'type',
              templateOptions: {
                options: $ctrl.typeOptions,
                valueProp: 'id',
                labelProp: 'name',
                label: $translate.instant('TYPE'),
                required: true,
              },
              defaultValue: $ctrl.typeOptions.length > 0 ? $ctrl.typeOptions[0].id : null,
            },
            {
              className: 'col-xs-12 col-sm-6 px-0 pl-md-base',
              type: 'input',
              key: 'version',
              templateOptions: {
                label: $translate.instant('VERSION'),
                required: true,
              },
              defaultValue: '1.0',
            },
          ],
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
              },
            },
            {
              className: 'col-xs-12 col-sm-6 px-0 pl-md-base',
              type: 'datepicker',
              key: 'end_date',
              templateOptions: {
                label: $translate.instant('ACCESS.VALID_DATE_END'),
                appendToBody: false,
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

    $ctrl.buildNodeForm = function() {
      $ctrl.nodeFields = [
        {
          templateOptions: {
            label: $translate.instant('ACCESS.REFERENCE_CODE'),
            type: 'text',
            required: true,
            focus: true,
          },
          type: 'input',
          key: 'reference_code',
        },
        {
          templateOptions: {
            type: 'text',
            label: $translate.instant('NAME'),
            required: true,
          },
          type: 'input',
          key: 'name',
        },
        {
          templateOptions: {
            label: $translate.instant('TYPE'),
            options: $ctrl.structureUnitTypes,
            valueProp: 'id',
            labelProp: 'name',
            required: true,
            notNull: true,
          },
          defaultValue: $ctrl.structureUnitTypes.length > 0 ? $ctrl.structureUnitTypes[0].id : null,
          type: 'select',
          key: 'type',
        },
        {
          templateOptions: {
            label: $translate.instant('DESCRIPTION'),
            type: 'text',
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
      return !angular.equals($ctrl.newNode, {});
    };

    $ctrl.removeNode = function() {
      $http
        .delete(appConfig.djangoUrl + 'structures/' + data.structure.id + '/units/' + $ctrl.node.id)
        .then(function(response) {
          Notifications.add($translate.instant('ACCESS.NODE_REMOVED'), 'success');
          EditMode.disable();
          $uibModalInstance.close('added');
        });
    };

    $ctrl.submit = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      if ($ctrl.changed()) {
        const parent = $ctrl.node.root ? null : $ctrl.node.id;
        $ctrl.submitting = true;
        $rootScope.skipErrorNotification = true;
        $http
          .post(
            appConfig.djangoUrl + 'structures/' + data.structure.id + '/units/',
            angular.extend($ctrl.newNode, {
              parent: parent,
            })
          )
          .then(function(response) {
            $ctrl.submitting = false;
            Notifications.add($translate.instant('ACCESS.NODE_ADDED'), 'success');
            EditMode.disable();
            $uibModalInstance.close(response.data);
          })
          .catch(function(response) {
            $ctrl.nonFieldErrors = response.data.non_field_errors;
            $ctrl.submitting = false;
          });
      }
    };
    /**
     * update new classification structure
     */
    $ctrl.update = function() {
      $ctrl.saving = true;
      $rootScope.skipErrorNotification = true;
      $http({
        method: 'PATCH',
        url: appConfig.djangoUrl + 'structures/' + data.structure.id + '/units/' + $ctrl.node.id + '/',
        data: {
          name: $ctrl.name,
        },
      })
        .then(function(response) {
          $ctrl.saving = false;
          $uibModalInstance.close(response.data);
          EditMode.disable();
          Notifications.add($translate.instant('NODE_UPDATED'), 'success');
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.saving = false;
        });
    };
    /**
     * Save new classification structure
     */
    $ctrl.save = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.creating = true;
      $rootScope.skipErrorNotification = true;
      Structure.new($ctrl.newStructure)
        .$promise.then(function(resource) {
          EditMode.disable();
          $ctrl.creating = false;
          $uibModalInstance.close(resource);
          Notifications.add($translate.instant('ACCESS.CLASSIFICATION_STRUCTURE_CREATED'), 'success');
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.creating = false;
        });
    };

    $ctrl.saveEditedStructure = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.saving = true;
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'structures/' + $ctrl.structure.id + '/',
        method: 'PATCH',
        data: $ctrl.structure,
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

    $ctrl.removing = false;
    $ctrl.remove = function(structure) {
      $ctrl.removing = true;
      Structure.remove({id: structure.id}).$promise.then(function(response) {
        $ctrl.removing = false;
        Notifications.add($translate.instant('ACCESS.CLASSIFICATION_STRUCTURE_REMOVED'), 'success');
        EditMode.disable();
        $uibModalInstance.close();
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
