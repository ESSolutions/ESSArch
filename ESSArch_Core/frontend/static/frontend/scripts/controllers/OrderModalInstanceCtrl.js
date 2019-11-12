export default class OrderModalInstanceCtrl {
  constructor(
    $uibModalInstance,
    data,
    $http,
    appConfig,
    listViewService,
    $translate,
    Utils,
    $q,
    EditMode,
    $scope,
    $window,
    $sce
  ) {
    const $ctrl = this;
    if (data) {
      $ctrl.data = data;
    }
    $ctrl.order = {};

    $ctrl.fields = [];
    $ctrl.options = {
      type: [],
      consign_method: [],
    };
    $ctrl.$onInit = () => {
      if (data.order) {
        $ctrl.order = angular.copy(data.order);
        $ctrl.order.type = angular.copy(data.order.type.id);
        delete $ctrl.order.responsible;
      }
      let promises = [];

      promises.push(
        $http.get(appConfig.djangoUrl + 'consign-methods/').then(response => {
          $ctrl.options.consign_method = angular.copy(response.data);
          return response.data;
        })
      );

      promises.push(
        $http.get(appConfig.djangoUrl + 'order-types/').then(response => {
          $ctrl.options.type = angular.copy(response.data);
          return response.data;
        })
      );

      $q.all(promises).then(responses => {
        if (!data.allow_close) {
          EditMode.enable();
        }
        $ctrl.buildForm();
      });
    };

    $ctrl.buildForm = () => {
      $ctrl.fields = [
        {
          key: 'label',
          type: 'input',
          templateOptions: {
            label: $translate.instant('LABEL'),
            required: true,
          },
        },
        {
          key: 'type',
          type: 'select',
          templateOptions: {
            label: $translate.instant('TYPE'),
            labelProp: 'name',
            valueProp: 'id',
            options: $ctrl.options.type,
            defaultValue: $ctrl.options.type.length > 0 ? $ctrl.options.type[0] : null,
            required: true,
          },
        },
        {
          key: 'consign_method',
          type: 'select',
          templateOptions: {
            label: $translate.instant('CONSIGN_METHOD'),
            labelProp: 'name',
            valueProp: 'id',
            options: $ctrl.options.consign_method,
            defaultValue: $ctrl.options.consign_method.length > 0 ? $ctrl.options.consign_method[0] : null,
          },
        },
        {
          key: 'personal_number',
          type: 'input',
          templateOptions: {
            label: $translate.instant('PERSONAL_NUMBER'),
          },
        },
        {
          key: 'first_name',
          type: 'input',
          templateOptions: {
            label: $translate.instant('FIRST_NAME'),
          },
        },
        {
          key: 'family_name',
          type: 'input',
          templateOptions: {
            label: $translate.instant('FAMILY_NAME'),
          },
        },
        {
          key: 'address',
          type: 'input',
          templateOptions: {
            label: $translate.instant('ADDRESS'),
          },
        },
        {
          key: 'postal_code',
          type: 'input',
          templateOptions: {
            label: $translate.instant('POSTAL_CODE'),
          },
        },
        {
          key: 'city',
          type: 'input',
          templateOptions: {
            label: $translate.instant('CITY'),
          },
        },
        {
          key: 'phone',
          type: 'input',
          templateOptions: {
            label: $translate.instant('PHONE'),
          },
        },
        {
          key: 'order_content',
          type: 'textarea',
          templateOptions: {
            label: $translate.instant('ORDER_CONTENT'),
            rows: 3,
          },
        },
      ];
    };

    $ctrl.newOrder = function(order) {
      $ctrl.creatingOrder = true;
      listViewService
        .prepareOrder(order)
        .then(function(result) {
          EditMode.disable();
          $ctrl.creatingOrder = false;
          $uibModalInstance.close();
        })
        .catch(function(response) {
          $ctrl.creatingOrder = false;
        });
    };
    $ctrl.save = () => {
      $ctrl.saving = true;
      $http({
        method: 'PATCH',
        url: appConfig.djangoUrl + 'orders/' + data.order.id + '/',
        data: Utils.getDiff(data.order, $ctrl.order, {map: {type: 'id'}}),
      })
        .then(response => {
          $ctrl.saving = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(response => {
          $ctrl.saving = false;
        });
    };

    $ctrl.download = () => {
      const showFile = $sce.trustAsResourceUrl(appConfig.djangoUrl + 'orders/' + data.order.id + '/download/');
      $window.open(showFile, '_blank');
      $uibModalInstance.close();
    };

    $ctrl.remove = function(order) {
      $ctrl.removing = true;
      $http({
        method: 'DELETE',
        url: appConfig.djangoUrl + 'orders/' + order.id + '/',
      })
        .then(function() {
          $ctrl.removing = false;
          EditMode.disable();
          $uibModalInstance.close();
        })
        .catch(function() {
          $ctrl.removing = false;
        });
    };
    $ctrl.ok = function() {
      $uibModalInstance.close();
    };
    $ctrl.cancel = function() {
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
