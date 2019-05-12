angular
  .module('essarch.controllers')
  .controller('EditStructureUnitModalInstanceCtrl', function(
    Search,
    $translate,
    $uibModalInstance,
    djangoAuth,
    appConfig,
    $http,
    data,
    $scope,
    Notifications,
    $timeout,
    $q
  ) {
    var $ctrl = this;
    $ctrl.editNode = {};
    $ctrl.options = {};
    $ctrl.nodeFields = [];
    $ctrl.types = [];
    $ctrl.$onInit = function() {
      if (data.node) {
        $ctrl.node = data.node;
        $ctrl.editNode = angular.copy($ctrl.node);
      }
      if (data.structure) {
        $ctrl.structure = data.structure;
      }

      $ctrl.nodeFields = [
        {
          templateOptions: {
            label: $translate.instant('ACCESS.REFERENCE_CODE'),
            type: 'text',
            focus: true,
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
          },
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
      return !angular.equals($ctrl.editNode, $ctrl.node);
    };
    /**
     * update new classification structure
     */
    $ctrl.saving = false;
    $ctrl.update = function() {
      $ctrl.saving = true;
      $http({
        method: 'PATCH',
        url: appConfig.djangoUrl + 'classification-structures/' + data.structure.id + '/units/' + $ctrl.node.id + '/',
        data: $ctrl.editNode,
      })
        .then(function(response) {
          $ctrl.saving = false;
          Notifications.add($translate.instant('ACCESS.NODE_EDITED'), 'success');
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.saving = false;
        });
    };

    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  });
