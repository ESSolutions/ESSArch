angular.module('essarch.controllers').controller('NodeDeliveryModalInstanceCtrl', [
  'appConfig',
  '$http',
  '$translate',
  'data',
  '$uibModalInstance',
  '$scope',
  'EditMode',
  'Utils',
  '$rootScope',
  '$q',
  'Notifications',
  function(
    appConfig,
    $http,
    $translate,
    data,
    $uibModalInstance,
    $scope,
    EditMode,
    Utils,
    $rootScope,
    $q,
    Notifications
  ) {
    var $ctrl = this;
    $ctrl.model = {};
    $ctrl.$onInit = function() {
      if (data.nodes) {
        $ctrl.nodes = $ctrl.filterNodes(angular.copy(data.nodes));
      } else if (data.node) {
        $ctrl.node = angular.copy(data.node);
      }
      $ctrl.buildForm();
    };

    $ctrl.getDeliveries = function(search) {
      return $http.get(appConfig.djangoUrl + 'deliveries/', {params: {search: search}}).then(function(response) {
        $ctrl.deliveries = response.data;
        return response.data;
      });
    };

    $ctrl.getTransfers = function(search) {
      if ($ctrl.model.delivery === null || angular.isUndefined($ctrl.model.delivery)) {
        var deferred = $q.defer();
        deferred.resolve([]);
        return deferred.promise;
      } else {
        return $http
          .get(appConfig.djangoUrl + 'deliveries/' + $ctrl.model.delivery + '/transfers/', {params: {search: search}})
          .then(function(response) {
            $ctrl.transfers = response.data;
            return response.data;
          });
      }
    };

    $ctrl.buildForm = function() {
      $ctrl.fields = [
        {
          type: 'uiselect',
          key: 'delivery',
          templateOptions: {
            required: true,
            options: function() {
              return $ctrl.deliveries;
            },
            valueProp: 'id',
            labelProp: 'name',
            placeholder: $translate.instant('ACCESS.DELIVERY'),
            label: $translate.instant('ACCESS.DELIVERY'),
            appendToBody: false,
            onChange: function($modelValue) {
              $ctrl.model.transfer = null;
            },
            optionsFunction: function(search) {
              return $ctrl.deliveries;
            },
            refresh: function(search) {
              $ctrl.getDeliveries(search).then(function() {
                this.options = $ctrl.deliveries;
              });
            },
          },
        },
        {
          type: 'uiselect',
          key: 'transfer',
          templateOptions: {
            required: true,
            options: function() {
              return $ctrl.transfers;
            },
            valueProp: 'id',
            labelProp: 'name',
            placeholder: $translate.instant('ACCESS.TRANSFER'),
            label: $translate.instant('ACCESS.TRANSFER'),
            appendToBody: false,
            optionsFunction: function(search) {
              return $ctrl.transfers;
            },
            refresh: function(search) {
              $ctrl.getTransfers(search).then(function() {
                this.options = $ctrl.transfers;
              });
            },
          },
        },
      ];
    };

    $ctrl.filterNodes = function(nodes) {
      var filtered = [];
      nodes.forEach(function(x) {
        if (!angular.isUndefined(x) && x.placeholder !== true && x.type !== 'agent') {
          filtered.push(x);
        }
      });
      return filtered;
    };

    $ctrl.cancel = function() {
      EditMode.disable();
      $uibModalInstance.dismiss('cancel');
    };

    $ctrl.save = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.saving = true;
      var structureUnits = [];
      var tags = [];
      if ($ctrl.nodes && $ctrl.nodes.length > 0) {
        $ctrl.nodes.forEach(function(x) {
          if (x._is_structure_unit) {
            structureUnits.push(x);
          } else {
            tags.push(x);
          }
        });
      } else if ($ctrl.node) {
        if ($ctrl.node._is_structure_unit) {
          structureUnits.push($ctrl.node);
        } else {
          tags.push($ctrl.node);
        }
      }
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'transfers/' + $ctrl.model.transfer + '/add-nodes/',
        method: 'POST',
        data: {
          structure_units: structureUnits.map(function(x) {
            return x.id;
          }),
          tags: tags.map(function(x) {
            return x.id;
          }),
        },
      })
        .then(function(response) {
          Notifications.add($translate.instant('ACCESS.ADDED_TO_TRANSFER'), 'success');
          $ctrl.saving = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.saving = false;
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
  },
]);
