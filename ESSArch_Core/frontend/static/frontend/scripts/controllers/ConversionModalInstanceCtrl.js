import 'later/later.js';
import prettyCron from 'prettycron';

export default class ConversionModalInstanceCtrl {
  constructor(cronService, $filter, $translate, IP, $uibModalInstance, appConfig, $http, data, Notifications) {
    const $ctrl = this;
    // Set later to use local time for next job
    later.date.localTime();
    $ctrl.angular = angular;
    $ctrl.data = data;
    $ctrl.requestTypes = data.types;
    $ctrl.request = data.request;
    $ctrl.conversionTemplates = [];
    $ctrl.ip = null;
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

    $ctrl.cronConfig = {
      allowMultiple: true,
    };
    $ctrl.frequency = '* * * * *';
    $ctrl.myFrequency = null;

    $ctrl.validCron = function(frequency) {
      const months = [
        {name: 'jan', days: 31},
        {name: 'feb', days: 29},
        {name: 'mar', days: 31},
        {name: 'apr', days: 30},
        {name: 'may', days: 31},
        {name: 'jun', days: 30},
        {name: 'jul', days: 31},
        {name: 'aug', days: 31},
        {name: 'sep', days: 30},
        {name: 'okt', days: 31},
        {name: 'nov', days: 30},
        {name: 'dec', days: 31},
      ];
      const cron = cronService.fromCron(frequency, true);
      if (cron.monthValues && cron.dayOfMonthValues) {
        return !cron.monthValues
          .map(function(month) {
            return !cron.dayOfMonthValues
              .map(function(day) {
                return months[month - 1].days >= day;
              })
              .includes(false);
          })
          .includes(false);
      } else {
        return true;
      }
    };

    $ctrl.prettyFrequency = function(frequency) {
      if ($ctrl.validCron(frequency)) {
        return prettyCron.toString(frequency);
      } else {
        return $translate.instant('ARCHIVE_MAINTENANCE.INVALID_FREQUENCY');
      }
    };
    $ctrl.nextPretty = function(frequency) {
      if ($ctrl.validCron(frequency)) {
        return $filter('date')(prettyCron.getNextDate(frequency), 'yyyy-MM-dd HH:mm:ss');
      } else {
        return '...';
      }
    };

    function getTemplates() {
      IP.conversionTemplates({id: ip.id}).$promise.then(function(resource) {
        ip.templates = resource;
      });
    }
    if (data.preview && data.job) {
      $http.get(appConfig.djangoUrl + 'conversion-jobs/' + data.job.id + '/preview/').then(function(response) {
        $ctrl.jobPreview = response.data;
      });
    }
    $ctrl.addTemplate = function(ip, template) {
      $ctrl.addingTemplate = true;
      $http({
        url: appConfig.djangoUrl + 'information-packages/' + ip.id + '/add-conversion-template/',
        method: 'POST',
        data: {
          id: template.id,
        },
      })
        .then(function(response) {
          $ctrl.addingTemplate = false;
          ip.templates.push(template);
          $ctrl.showTemplatesTable(ip);
        })
        .catch(function(response) {
          $ctrl.addingTemplate = false;
        });
    };

    $ctrl.specifications = {};
    $ctrl.addSpecification = function() {
      $ctrl.specifications[$ctrl.path] = {
        target: $ctrl.target,
        tool: $ctrl.tool,
      };
      $ctrl.path = '';
      $ctrl.target = '';
    };

    $ctrl.deleteSpecification = function(key) {
      delete $ctrl.specifications[key];
    };

    $ctrl.removeTemplate = function(ip, template) {
      $ctrl.removingTemplate = true;
      $http({
        url: appConfig.djangoUrl + 'information-packages/' + ip.id + '/remove-conversion-template/',
        method: 'POST',
        data: {
          id: template.id,
        },
      })
        .then(function(response) {
          ip.templates.forEach(function(x, index, array) {
            if (x.id == template.id) {
              array.splice(index, 1);
            }
          });
          $ctrl.removingTemplate = false;
          $ctrl.showTemplatesTable(ip);
        })
        .catch(function(response) {
          $ctrl.removingTemplate = false;
        });
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
      if (angular.equals($ctrl.specifications, {})) {
        $ctrl.showRequired = true;
        $ctrl.addingTemplate = false;
        return;
      }
      $ctrl.data = {
        name: $ctrl.name,
        frequency: $ctrl.manualTemplate ? '' : $ctrl.frequency,
        specification: $ctrl.specifications,
        public: $ctrl.publicTemplate,
        description: $ctrl.description,
      };
      $http({
        url: appConfig.djangoUrl + 'conversion-templates/',
        method: 'POST',
        data: $ctrl.data,
      })
        .then(function(response) {
          $ctrl.addingTemplate = false;
          Notifications.add($translate.instant('ARCHIVE_MAINTENANCE.TEMPLATE_CREATED'), 'success');
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
          $uibModalInstance.close();
        })
        .catch(function(response) {
          $ctrl.removingTemplate = false;
        });
    };

    $ctrl.ok = function() {
      $uibModalInstance.close();
    };
    $ctrl.cancel = function() {
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
  }
}
