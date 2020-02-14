export default class AppraisalModalInstanceCtrl {
  constructor($filter, $translate, IP, $uibModalInstance, appConfig, $http, data, Notifications, Utils) {
    const $ctrl = this;
    // Set later to use local time for next job
    $ctrl.angular = angular;
    $ctrl.data = data;
    $ctrl.requestTypes = data.types;
    $ctrl.request = data.request;
    $ctrl.appraisalTemplates = [];
    $ctrl.publicTemplate = true;
    $ctrl.manualTemplate = false;
    $ctrl.ip = null;
    $ctrl.model = {specification: []};
    $ctrl.$onInit = () => {
      if (data.appraisal) {
        $ctrl.model = angular.copy(data.appraisal);
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
      },
    ];

    $ctrl.showTemplatesTable = function(ip) {
      $ctrl.ip = ip;
      return $http
        .get(appConfig.djangoUrl + 'appraisal-templates/', {params: {not_related_to_ip: ip.id}})
        .then(function(response) {
          $ctrl.appraisalTemplates = response.data;
        });
    };
    if (data.preview && data.job) {
      $http.get(appConfig.djangoUrl + 'appraisal-jobs/' + data.job.id + '/preview/').then(function(response) {
        $ctrl.jobPreview = response.data;
      });
    }
    $ctrl.expandIp = function(ip) {
      if (ip.expanded) {
        ip.expanded = false;
      } else {
        ip.expanded = true;
        IP.appraisalTemplates({id: ip.id}).$promise.then(function(resource) {
          ip.templates = resource;
        });
      }
    };

    $ctrl.addTemplate = function(ip, template) {
      $ctrl.addingTemplate = true;
      $http({
        url: appConfig.djangoUrl + 'information-packages/' + ip.id + '/add-appraisal-template/',
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
    $ctrl.removeTemplate = function(ip, template) {
      $ctrl.removingTemplate = true;
      $http({
        url: appConfig.djangoUrl + 'information-packages/' + ip.id + '/remove-appraisal-template/',
        method: 'POST',
        data: {
          id: template.id,
        },
      })
        .then(function(response) {
          $ctrl.removingTemplate = false;
          ip.templates.forEach(function(x, index, array) {
            if (x.id == template.id) {
              array.splice(index, 1);
            }
          });
          $ctrl.showTemplatesTable(ip);
        })
        .catch(function(response) {
          $ctrl.removingTemplate = false;
        });
    };
    $ctrl.closeTemplatesTable = function() {
      $ctrl.appraisalTemplates = [];
      $ctrl.ip = null;
    };

    $ctrl.createJob = function(template) {
      $ctrl.creatingJob = true;
      $http({
        url: appConfig.djangoUrl + 'appraisal-jobs/',
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
        url: appConfig.djangoUrl + 'appraisal-jobs/',
        method: 'POST',
        data: {template: template.id},
      })
        .then(function(response) {
          $http({
            url: appConfig.djangoUrl + 'appraisal-jobs/' + response.data.id + '/run/',
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
        $ctrl.model.specification.push(path);
      }
      $ctrl.path = '';
    };
    $ctrl.removePath = function(path) {
      $ctrl.pathList.splice($ctrl.pathList.indexOf(path), 1);
    };
    $ctrl.appraisalTemplate = null;
    $ctrl.create = function() {
      $ctrl.addingTemplate = true;
      if ($ctrl.pathList.length == 0) {
        $ctrl.showRequired = true;
        $ctrl.addingTemplate = false;
        return;
      }
      if ($ctrl.createForm.$invalid) {
        $ctrl.createForm.$setSubmitted();
        return;
      }

      $http({
        url: appConfig.djangoUrl + 'appraisal-templates/',
        method: 'POST',
        data: $ctrl.model,
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

    $ctrl.save = function(template) {
      $ctrl.saving = true;
      if ($ctrl.pathList.length == 0) {
        $ctrl.showRequired = true;
        $ctrl.saving = false;
        return;
      }
      if ($ctrl.createForm.$invalid) {
        $ctrl.createForm.$setSubmitted();
        return;
      }
      $ctrl.data = Utils.getDiff(data.appraisal, $ctrl.model, {map: {}});
      $http({
        url: appConfig.djangoUrl + 'appraisal-templates/' + template.id + '/',
        method: 'PATCH',
        data: $ctrl.data,
      })
        .then(function(response) {
          $ctrl.saving = false;
          $uibModalInstance.close($ctrl.data);
        })
        .catch(function(response) {
          $ctrl.saving = false;
        });
    };

    $ctrl.removeAppraisal = function() {
      $ctrl.removingTemplate = true;
      const appraisal = data.appraisal;
      $http({
        url: appConfig.djangoUrl + 'appraisal-templates/' + appraisal.id,
        method: 'DELETE',
      })
        .then(function(response) {
          $ctrl.removingTemplate = false;
          Notifications.add(
            $translate.instant('ARCHIVE_MAINTENANCE.APPRAISAL_TEMPLATE_REMOVED', {name: appraisal.name}),
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
    $ctrl.submitAppraisal = function(appraisal) {
      Notifications.add(
        $translate.instant('ARCHIVE_MAINTENANCE.NODE_ADDED_TO_APPRAISAL_TEMPLATE', {
          node: $ctrl.data.record.name,
          template: appraisal.name,
        }),
        'success'
      );
      $uibModalInstance.close(appraisal);
    };
  }
}
