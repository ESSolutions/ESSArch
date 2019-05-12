angular
  .module('essarch.controllers')
  .controller('AppraisalModalInstanceCtrl', function(
    cronService,
    $filter,
    $translate,
    IP,
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
    // Set later to use local time for next job
    later.date.localTime();
    $ctrl.angular = angular;
    $ctrl.data = data;
    $ctrl.requestTypes = data.types;
    $ctrl.request = data.request;
    $ctrl.appraisalRules = [];
    $ctrl.publicRule = true;
    $ctrl.manualRule = false;
    $ctrl.ip = null;
    $ctrl.showRulesTable = function(ip) {
      $ctrl.ip = ip;
      return $http
        .get(appConfig.djangoUrl + 'appraisal-rules/', {params: {not_related_to_ip: ip.id}})
        .then(function(response) {
          $ctrl.appraisalRules = response.data;
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
        IP.appraisalRules({id: ip.id}).$promise.then(function(resource) {
          ip.rules = resource;
        });
      }
    };
    $ctrl.cronConfig = {
      allowMultiple: true,
    };
    $ctrl.frequency = '* * * * *';
    $ctrl.myFrequency = null;

    $ctrl.validCron = function(frequency) {
      var months = [
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
      var cron = cronService.fromCron(frequency, true);
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

    $ctrl.addRule = function(ip, rule) {
      $ctrl.addingRule = true;
      $http({
        url: appConfig.djangoUrl + 'information-packages/' + ip.id + '/add-appraisal-rule/',
        method: 'POST',
        data: {
          id: rule.id,
        },
      })
        .then(function(response) {
          $ctrl.addingRule = false;
          ip.rules.push(rule);
          $ctrl.showRulesTable(ip);
        })
        .catch(function(response) {
          $ctrl.addingRule = false;
        });
    };
    $ctrl.removeRule = function(ip, rule) {
      $ctrl.removingRule = true;
      $http({
        url: appConfig.djangoUrl + 'information-packages/' + ip.id + '/remove-appraisal-rule/',
        method: 'POST',
        data: {
          id: rule.id,
        },
      })
        .then(function(response) {
          $ctrl.removingRule = false;
          ip.rules.forEach(function(x, index, array) {
            if (x.id == rule.id) {
              array.splice(index, 1);
            }
          });
          $ctrl.showRulesTable(ip);
        })
        .catch(function(response) {
          $ctrl.removingRule = false;
        });
    };
    $ctrl.closeRulesTable = function() {
      $ctrl.appraisalRules = [];
      $ctrl.ip = null;
    };

    $ctrl.createJob = function(rule) {
      $ctrl.creatingJob = true;
      $http({
        url: appConfig.djangoUrl + 'appraisal-jobs/',
        method: 'POST',
        data: {rule: rule.id},
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
    $ctrl.createJobAndStart = function(rule) {
      $ctrl.runningJob = true;
      $http({
        url: appConfig.djangoUrl + 'appraisal-jobs/',
        method: 'POST',
        data: {rule: rule.id},
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
        $ctrl.pathList.push(path);
      }
      $ctrl.path = '';
    };
    $ctrl.removePath = function(path) {
      $ctrl.pathList.splice($ctrl.pathList.indexOf(path), 1);
    };
    $ctrl.appraisalRule = null;
    $ctrl.create = function() {
      $ctrl.addingRule = true;
      if ($ctrl.pathList.length == 0) {
        $ctrl.showRequired = true;
        $ctrl.addingRule = false;
        return;
      }
      $ctrl.data = {
        name: $ctrl.name,
        frequency: $ctrl.manualRule ? '' : $ctrl.frequency,
        specification: $ctrl.pathList,
        public: $ctrl.publicRule,
        description: $ctrl.description,
      };
      $http({
        url: appConfig.djangoUrl + 'appraisal-rules/',
        method: 'POST',
        data: $ctrl.data,
      })
        .then(function(response) {
          $ctrl.addingRule = false;
          Notifications.add($translate.instant('ARCHIVE_MAINTENANCE.RULE_CREATED'), 'success');
          $uibModalInstance.close($ctrl.data);
        })
        .catch(function(response) {
          $ctrl.addingRule = false;
        });
    };

    $ctrl.removeAppraisal = function() {
      $ctrl.removingRule = true;
      var appraisal = data.appraisal;
      $http({
        url: appConfig.djangoUrl + 'appraisal-rules/' + appraisal.id,
        method: 'DELETE',
      })
        .then(function(response) {
          $ctrl.removingRule = false;
          Notifications.add(
            $translate.instant('ARCHIVE_MAINTENANCE.APPRAISAL_RULE_REMOVED', {name: appraisal.name}),
            'success'
          );
          $uibModalInstance.close();
        })
        .catch(function(response) {
          $ctrl.removingRule = false;
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
        $translate.instant('ARCHIVE_MAINTENANCE.NODE_ADDED_TO_APPRAISAL_RULE', {
          node: $ctrl.data.record.name,
          rule: appraisal.name,
        }),
        'success'
      );
      $uibModalInstance.close(appraisal);
    };
  });
