export default class ConversionModalInstanceCtrl {
  constructor($translate, IP, $uibModalInstance, appConfig, $http, data, Notifications, $scope, EditMode) {
    const $ctrl = this;
    $ctrl.angular = angular;
    $ctrl.data = data;
    $ctrl.ip = null;
    $ctrl.model = {
      specification: {},
    };

    $ctrl.$onInit = () => {
      if (!data.allow_close) {
        EditMode.enable();
      }
      if (data.conversion) {
        $ctrl.model = angular.copy(data.conversion);
      }
    };

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
        type: 'textarea',
        key: 'description',
        templateOptions: {
          label: $translate.instant('DESCRIPTION'),
          rows: 3,
        },
      },
      {
        type: 'checkbox',
        key: 'public',
        templateOptions: {
          label: $translate.instant('PUBLIC'),
        },
        defaultValue: true,
      },
    ];

    $ctrl.create = function () {
      $ctrl.addingTemplate = true;
      $http({
        url: appConfig.djangoUrl + 'conversion-templates/',
        method: 'POST',
        data: $ctrl.model,
      })
        .then(function (response) {
          $ctrl.addingTemplate = false;
          Notifications.add($translate.instant('ARCHIVE_MAINTENANCE.TEMPLATE_CREATED'), 'success');
          EditMode.disable();
          $uibModalInstance.close($ctrl.data);
        })
        .catch(function (response) {
          $ctrl.addingTemplate = false;
        });
    };

    $ctrl.save = function () {
      $ctrl.addingTemplate = true;
      $http({
        url: appConfig.djangoUrl + 'conversion-templates/' + data.conversion.id + '/',
        method: 'PATCH',
        data: $ctrl.model,
      })
        .then(function (response) {
          $ctrl.addingTemplate = false;
          EditMode.disable();
          $uibModalInstance.close($ctrl.data);
        })
        .catch(function (response) {
          $ctrl.addingTemplate = false;
        });
    };

    $ctrl.removeConversion = function () {
      $ctrl.removingTemplate = true;
      const conversion = data.conversion;
      $http({
        url: appConfig.djangoUrl + 'conversion-templates/' + conversion.id,
        method: 'DELETE',
      })
        .then(function (response) {
          $ctrl.removingTemplate = false;
          Notifications.add(
            $translate.instant('ARCHIVE_MAINTENANCE.CONVERSION_TEMPLATE_REMOVED', {name: conversion.name}),
            'success'
          );
          EditMode.disable();
          $uibModalInstance.close();
        })
        .catch(function (response) {
          $ctrl.removingTemplate = false;
        });
    };

    $ctrl.ok = function () {
      EditMode.disable();
      $uibModalInstance.close();
    };

    $ctrl.cancel = function () {
      EditMode.disable();
      $uibModalInstance.dismiss('cancel');
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
