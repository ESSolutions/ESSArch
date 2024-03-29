export default class TransferModalInstanceCtrl {
  constructor(appConfig, $http, $translate, data, $uibModalInstance, $scope, EditMode, Utils, $rootScope) {
    const $ctrl = this;
    $ctrl.transfer = {};
    $ctrl.$onInit = function () {
      if (!data.remove) {
        if (data.transfer) {
          $ctrl.transfer = angular.copy(data.transfer);
        }
        $ctrl.buildForm();
      } else {
        if (data.transfer) {
          $ctrl.transfer = angular.copy(data.transfer);
        }
      }
    };
    $ctrl.buildForm = function () {
      $ctrl.fields = [
        {
          type: 'input',
          key: 'name',
          templateOptions: {
            focus: true,
            label: $translate.instant('NAME'),
            required: true,
            maxlength: 255,
          },
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
          key: 'submitter_information',
          type: 'checkbox',
          templateOptions: {
            label: $translate.instant('ACCESS.SUBMITTER_INFO'),
          },
        },
        {
          type: 'input',
          key: 'submitter_organization',
          expressionProperties: {
            hide: function ($modelValue) {
              return !$ctrl.transfer.submitter_information;
            },
          },
          templateOptions: {
            label: $translate.instant('ACCESS.SUBMITTER_ORGANIZATION'),
            maxlength: 255,
          },
        },
        {
          type: 'input',
          key: 'submitter_organization_main_address',
          expressionProperties: {
            hide: function ($modelValue) {
              return !$ctrl.transfer.submitter_information;
            },
          },
          templateOptions: {
            label: $translate.instant('ACCESS.SUBMITTER_ORGANIZATION_MAIN_ADDRESS'),
            maxlength: 255,
          },
        },
        {
          type: 'input',
          key: 'submitter_individual_name',
          expressionProperties: {
            hide: function ($modelValue) {
              return !$ctrl.transfer.submitter_information;
            },
          },
          templateOptions: {
            label: $translate.instant('ACCESS.SUBMITTER_INDIVIDUAL_NAME'),
            maxlength: 255,
          },
        },
        {
          type: 'input',
          key: 'submitter_individual_phone',
          expressionProperties: {
            hide: function ($modelValue) {
              return !$ctrl.transfer.submitter_information;
            },
          },
          templateOptions: {
            label: $translate.instant('ACCESS.SUBMITTER_INDIVIDUAL_PHONE'),
            maxlength: 255,
          },
        },
        {
          type: 'input',
          key: 'submitter_individual_email',
          expressionProperties: {
            hide: function ($modelValue) {
              return !$ctrl.transfer.submitter_information;
            },
          },
          templateOptions: {
            label: $translate.instant('ACCESS.SUBMITTER_INDIVIDUAL_EMAIL'),
            maxlength: 255,
          },
        },
      ];
    };

    $ctrl.cancel = function () {
      EditMode.disable();
      $uibModalInstance.dismiss('cancel');
    };
    $ctrl.create = function () {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.transfer.delivery = angular.copy(data.delivery);
      $ctrl.creating = true;
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'transfers/',
        method: 'POST',
        data: $ctrl.transfer,
      })
        .then(function (response) {
          $ctrl.creating = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function (response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.creating = false;
        });
    };

    $ctrl.save = function () {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.saving = true;
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'transfers/' + data.transfer.id + '/',
        method: 'PATCH',
        data: Utils.getDiff(data.transfer, $ctrl.transfer, {map: {type: 'id'}}),
      })
        .then(function (response) {
          $ctrl.saving = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function () {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.saving = false;
        });
    };

    $ctrl.remove = function () {
      $ctrl.removing = true;
      $rootScope.skipErrorNotification = true;
      $http
        .delete(appConfig.djangoUrl + 'transfers/' + $ctrl.transfer.id)
        .then(function (response) {
          $ctrl.removing = false;
          EditMode.disable();
          $uibModalInstance.close('removed');
        })
        .catch(function (response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.removing = false;
        });
    };

    $scope.$on('modal.closing', function (event, reason, closed) {
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
