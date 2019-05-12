angular
  .module('essarch.controllers')
  .controller('ClassificationModalInstanceCtrl', function(
    data,
    $http,
    appConfig,
    Notifications,
    $uibModalInstance,
    $translate,
    Structure
  ) {
    var $ctrl = this;
    $ctrl.name = null;
    $ctrl.newNode = {};
    $ctrl.options = {};
    $ctrl.nodeFields = [];
    $ctrl.types = [];
    $ctrl.data = data;
    $ctrl.$onInit = function() {
      if (data.node) {
        $ctrl.node = data.node;
      }
      if (data.structure) {
        $ctrl.structure = data.structure;
      }

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
            type: 'text',
            options: [
              {
                name: 'Verksamhetsområde',
                value: 'Verksamhetsområde',
              },
              {
                name: 'Processgrupp',
                value: 'Processgrupp',
              },
              {
                name: 'Process',
                value: 'Process',
              },
            ],
            required: true,
          },
          defaultValue: 'Verksamhetsområde',
          type: 'select',
          key: 'type',
        },
        {
          templateOptions: {
            label: $translate.instant('ACCESS.DESCRIPTION'),
            type: 'text',
            rows: 3,
          },
          type: 'textarea',
          key: 'description',
        },
        {
          templateOptions: {
            type: 'text',
            label: $translate.instant('START_DATE'),
            appendToBody: false,
          },
          type: 'datepicker',
          key: 'start_date',
        },
        {
          templateOptions: {
            type: 'text',
            label: $translate.instant('END_DATE'),
            appendToBody: false,
          },
          type: 'datepicker',
          key: 'end_date',
        },
      ];
    };

    $ctrl.changed = function() {
      return !angular.equals($ctrl.newNode, {});
    };

    $ctrl.remove = function() {
      $http
        .delete(appConfig.djangoUrl + 'classification-structures/' + data.structure.id + '/units/' + $ctrl.node.id)
        .then(function(response) {
          Notifications.add($translate.instant('ACCESS.NODE_REMOVED'), 'success');
          $uibModalInstance.close('added');
        });
    };

    $ctrl.submit = function() {
      if ($ctrl.changed()) {
        $ctrl.submitting = true;
        $http
          .post(
            appConfig.djangoUrl + 'classification-structures/' + data.structure.id + '/units/',
            angular.extend($ctrl.newNode, {
              parent: $ctrl.node.id,
            })
          )
          .then(function(response) {
            $ctrl.submitting = false;
            Notifications.add($translate.instant('ACCESS.NODE_ADDED'), 'success');
            $uibModalInstance.close(response.data);
          })
          .catch(function(response) {
            $ctrl.submitting = false;
          });
      }
    };
    /**
     * update new classification structure
     */
    $ctrl.update = function() {
      $http({
        method: 'PATCH',
        url: appConfig.djangoUrl + 'classification-structures/' + data.structure.id + '/units/' + $ctrl.node.id + '/',
        data: {
          name: $ctrl.name,
        },
      }).then(function(response) {
        $uibModalInstance.close(response.data);
        Notifications.add($translate.instant('NODE_UPDATED'), 'success');
      });
    };
    /**
     * Save new classification structure
     */
    $ctrl.save = function() {
      Structure.new({
        name: $ctrl.name,
        start_date: $ctrl.startDate,
        end_date: $ctrl.endDate,
        level: $ctrl.level,
      }).$promise.then(function(response) {
        $uibModalInstance.close(response.data);
        Notifications.add($translate.instant('ACCESS.CLASSIFICATION_STRUCTURE_CREATED'), 'success');
      });
    };

    $ctrl.removing = false;
    $ctrl.remove = function(structure) {
      $ctrl.removing = true;
      Structure.remove({id: structure.id}).$promise.then(function(response) {
        $ctrl.removing = false;
        Notifications.add($translate.instant('ACCESS.CLASSIFICATION_STRUCTURE_REMOVED'), 'success');
        $uibModalInstance.close();
      });
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  });
