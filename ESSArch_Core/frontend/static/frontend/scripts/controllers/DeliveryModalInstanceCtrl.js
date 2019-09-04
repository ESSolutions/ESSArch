export default class DeliveryModalInstanceCtrl {
  constructor(appConfig, $http, $translate, data, $uibModalInstance, $scope, EditMode, Utils, $rootScope, AgentName) {
    const $ctrl = this;
    $ctrl.delivery = {};
    $ctrl.options = {};
    $ctrl.$onInit = function() {
      if (!data.remove) {
        if (data.delivery) {
          $ctrl.delivery = angular.copy(data.delivery);
          $ctrl.delivery.type = angular.copy(data.delivery.type.id);
          if ($ctrl.delivery.producer_organization) {
            $ctrl.delivery.producer_organization.full_name = AgentName.getAuthorizedName(
              angular.copy($ctrl.delivery.producer_organization)
            ).full_name;
          }
        }
        $ctrl.getDeliveryTypes().then(function(response) {
          EditMode.enable();
          $ctrl.buildForm();
        });
      } else {
        if (data.delivery) {
          $ctrl.delivery = angular.copy(data.delivery);
        }
      }
    };

    $ctrl.getDeliveryTypes = function(search) {
      return $http.get(appConfig.djangoUrl + 'delivery-types/').then(function(response) {
        $ctrl.deliveryTypes = response.data;
        return response.data;
      });
    };

    $ctrl.getAgents = function(search) {
      return $http({
        url: appConfig.djangoUrl + 'agents/',
        mathod: 'GET',
        params: {page: 1, page_size: 10, search: search},
      }).then(function(response) {
        response.data.forEach(function(agent) {
          AgentName.parseAgentNames(agent);
        });
        $ctrl.options.agents = response.data;
        return $ctrl.options.agents;
      });
    };

    $ctrl.getSas = function(search) {
      return $http({
        url: appConfig.djangoUrl + 'submission-agreements/',
        mathod: 'GET',
        params: {page: 1, page_size: 10, search: search, published: true},
      }).then(function(response) {
        $ctrl.options.sas = response.data;
        return $ctrl.options.sas;
      });
    };

    $ctrl.buildForm = function() {
      $ctrl.fields = [
        {
          type: 'input',
          key: 'name',
          templateOptions: {
            label: $translate.instant('NAME'),
            required: true,
          },
        },
        {
          type: 'select',
          key: 'type',
          templateOptions: {
            required: true,
            label: $translate.instant('TYPE'),
            labelProp: 'name',
            valueProp: 'id',
            options: $ctrl.deliveryTypes,
            notNull: true,
          },
          defaultValue: $ctrl.deliveryTypes.length > 0 ? $ctrl.deliveryTypes[0].id : null,
        },
        {
          type: 'textarea',
          key: 'description',
          templateOptions: {
            label: $translate.instant('DESCRIPTION'),
            rows: 3,
          },
        },
        {
          type: 'uiselect',
          key: 'producer_organization',
          templateOptions: {
            options: function() {
              return $ctrl.options.agents;
            },
            valueProp: 'id',
            labelProp: 'full_name',
            multiple: false,
            placeholder: $translate.instant('ACCESS.PRODUCER_ORGANIZATION'),
            label: $translate.instant('ACCESS.PRODUCER_ORGANIZATION'),
            appendToBody: false,
            refresh: function(search) {
              if ($ctrl.initAgentSearch && (angular.isUndefined(search) || search === null || search === '')) {
                search = angular.copy($ctrl.initAgentSearch);
                $ctrl.initAgentSearch = null;
              }
              $ctrl.getAgents(search);
            },
          },
          defaultValue: null,
        },
        {
          type: 'uiselect',
          key: 'submission_agreement',
          templateOptions: {
            options: function() {
              return $ctrl.options.sas;
            },
            valueProp: 'id',
            labelProp: 'name',
            multiple: false,
            placeholder: $translate.instant('SUBMISSION_AGREEMENT'),
            label: $translate.instant('SUBMISSION_AGREEMENT'),
            appendToBody: false,
            refresh: function(search) {
              if ($ctrl.initSaSearch && (angular.isUndefined(search) || search === null || search === '')) {
                search = angular.copy($ctrl.initSaSearch);
                $ctrl.initSaSearch = null;
              }
              $ctrl.getSas(search);
            },
          },
          defaultValue: null,
        },
        {
          type: 'input',
          key: 'reference_code',
          templateOptions: {
            label: $translate.instant('ACCESS.REFERENCE_CODE'),
          },
        },
      ];
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
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'deliveries/',
        method: 'POST',
        data: $ctrl.delivery,
      })
        .then(function(response) {
          $ctrl.creating = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.creating = false;
        });
    };
    $ctrl.save = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.saving = true;
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'deliveries/' + data.delivery.id + '/',
        method: 'PATCH',
        data: Utils.getDiff(data.delivery, $ctrl.delivery, {map: {type: 'id'}}),
      })
        .then(function(response) {
          $ctrl.saving = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function() {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.saving = false;
        });
    };

    $ctrl.remove = function() {
      $ctrl.removing = true;
      $rootScope.skipErrorNotification = true;
      $http
        .delete(appConfig.djangoUrl + 'deliveries/' + $ctrl.delivery.id)
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
