export default class ConversionModalInstanceCtrl {
  constructor($translate, IP, $uibModalInstance, appConfig, $http, data, Notifications, $scope, EditMode) {
    const $ctrl = this;
    $ctrl.angular = angular;
    $ctrl.data = data;
    $ctrl.conversionTemplates = [];
    $ctrl.ip = null;
    $ctrl.model = {
      package_file_pattern: {},
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

    $ctrl.showTemplatesTable = function(ip) {
      $ctrl.ip = ip;
      return $http
        .get(appConfig.djangoUrl + 'conversion-templates/', {params: {not_related_to_ip: ip.id}})
        .then(function(response) {
          $ctrl.conversionTemplates = response.data;
        });
    };

    $ctrl.expandIp = function(ip) {
      if (ip.expanded) {
        ip.expanded = false;
      } else {
        ip.expanded = true;
        IP.conversionTemplates({id: ip.id}).$promise.then(function(resource) {
          ip.templates = resource;
        });
      }
    };

    if (data.preview && data.job) {
      $http.get(appConfig.djangoUrl + 'conversion-jobs/' + data.job.id + '/preview/').then(function(response) {
        $ctrl.jobPreview = response.data;
      });
    }

    $ctrl.addSpecification = function() {
      $ctrl.model.package_file_pattern[$ctrl.path] = {
        target: $ctrl.target,
        tool: $ctrl.tool,
      };
      $ctrl.path = '';
      $ctrl.target = '';
    };

    $ctrl.deleteSpecification = function(key) {
      delete $ctrl.specifications[key];
    };

    $ctrl.closeTemplatesTable = function() {
      $ctrl.conversionTemplates = [];
      $ctrl.ip = null;
    };

    $ctrl.createJob = function(template) {
      $ctrl.creatingJob = true;
      $http({
        url: appConfig.djangoUrl + 'conversion-jobs/',
        method: 'POST',
        data: {template: template.id},
      })
        .then(function(response) {
          $ctrl.creatingJob = false;
          Notifications.add($translate.instant('ARCHIVE_MAINTENANCE.JOB_CREATED'), 'success');
          EditMode.disable();
          $uibModalInstance.close($ctrl.data);
        })
        .catch(function(response) {
          $ctrl.creatingJob = false;
        });
    };

    $ctrl.runningJob = false;
    $ctrl.createJobAndStart = function(template) {
      $ctrl.runningJob = true;
      $http({
        url: appConfig.djangoUrl + 'conversion-jobs/',
        method: 'POST',
        data: {template: template.id},
      })
        .then(function(response) {
          $http({
            url: appConfig.djangoUrl + 'conversion-jobs/' + response.data.id + '/run/',
            method: 'POST',
          })
            .then(function(response) {
              $ctrl.runningJob = false;
              Notifications.add($translate.instant('ARCHIVE_MAINTENANCE.JOB_RUNNING'), 'success');
              EditMode.disable();
              $uibModalInstance.close($ctrl.data);
            })
            .catch(function(response) {
              $ctrl.runningJob = false;
            });
        })
        .catch(function(response) {
          $ctrl.runningJob = false;
        });
    };

    $ctrl.path = '';
    $ctrl.pathList = [];
    $ctrl.addPath = function(path) {
      if (path.length > 0) {
        $ctrl.pathList.push(path);
      }
    };
    $ctrl.removePath = function(path) {
      $ctrl.pathList.splice($ctrl.pathList.indexOf(path), 1);
    };
    $ctrl.conversionTemplate = null;
    $ctrl.create = function() {
      $ctrl.addingTemplate = true;
      $http({
        url: appConfig.djangoUrl + 'conversion-templates/',
        method: 'POST',
        data: $ctrl.model,
      })
        .then(function(response) {
          $ctrl.addingTemplate = false;
          Notifications.add($translate.instant('ARCHIVE_MAINTENANCE.TEMPLATE_CREATED'), 'success');
          EditMode.disable();
          $uibModalInstance.close($ctrl.data);
        })
        .catch(function(response) {
          $ctrl.addingTemplate = false;
        });
    };

    $ctrl.save = function() {
      $ctrl.addingTemplate = true;
      $http({
        url: appConfig.djangoUrl + 'conversion-templates/' + data.conversion.id + '/',
        method: 'PATCH',
        data: $ctrl.model,
      })
        .then(function(response) {
          $ctrl.addingTemplate = false;
          EditMode.disable();
          $uibModalInstance.close($ctrl.data);
        })
        .catch(function(response) {
          $ctrl.addingTemplate = false;
        });
    };

    $ctrl.removeConversion = function() {
      $ctrl.removingTemplate = true;
      const conversion = data.conversion;
      $http({
        url: appConfig.djangoUrl + 'conversion-templates/' + conversion.id,
        method: 'DELETE',
      })
        .then(function(response) {
          $ctrl.removingTemplate = false;
          Notifications.add(
            $translate.instant('ARCHIVE_MAINTENANCE.CONVERSION_TEMPLATE_REMOVED', {name: conversion.name}),
            'success'
          );
          EditMode.disable();
          $uibModalInstance.close();
        })
        .catch(function(response) {
          $ctrl.removingTemplate = false;
        });
    };

    $ctrl.ok = function() {
      EditMode.disable();
      $uibModalInstance.close();
    };
    $ctrl.cancel = function() {
      EditMode.disable();
      $uibModalInstance.dismiss('cancel');
    };
    $ctrl.submitConversion = function(conversion) {
      Notifications.add(
        $translate.instant('ARCHIVE_MAINTENANCE.NODE_ADDED_TO_CONVERSION_TEMPLATE', {
          node: $ctrl.data.record.name,
          template: conversion.name,
        }),
        'success'
      );
      $uibModalInstance.close(conversion);
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
