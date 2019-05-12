angular
  .module('essarch.controllers')
  .controller('AddNodeModalInstanceCtrl', function(
    Search,
    $translate,
    $uibModalInstance,
    djangoAuth,
    appConfig,
    $http,
    data,
    $scope,
    Notifications,
    $timeout
  ) {
    var $ctrl = this;
    $ctrl.node = data.node.original;
    $ctrl.newNode = {
      reference_code: (data.node.children.length + 1).toString(),
      index: 'component',
    };
    $ctrl.options = {};
    $ctrl.nodeFields = [];
    $ctrl.types = [];

    $ctrl.$onInit = function() {
      $ctrl.indexes = [
        {
          name: 'component',
        },
      ];

      $ctrl.nodeFields = [
        {
          templateOptions: {
            type: 'text',
            label: $translate.instant('NAME'),
            required: true,
            focus: true,
          },
          type: 'input',
          key: 'name',
        },
        {
          templateOptions: {
            label: $translate.instant('TYPE'),
            type: 'text',
            required: true,
          },
          type: 'input',
          key: 'type',
        },
        {
          templateOptions: {
            label: $translate.instant('ACCESS.REFERENCE_CODE'),
            type: 'text',
            required: true,
          },
          type: 'input',
          key: 'reference_code',
        },
      ];
    };

    $ctrl.changed = function() {
      return !angular.equals($ctrl.newNode, {});
    };

    $ctrl.submit = function() {
      if ($ctrl.changed()) {
        $ctrl.submitting = true;
        var params = angular.extend($ctrl.newNode, {archive: data.archive, structure: data.structure});
        if ($ctrl.node._is_structure_unit) params.structure_unit = $ctrl.node._id;
        else {
          params.parent = $ctrl.node._id;
        }

        Search.addNode(params)
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
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  });
