export default class CreateAppraisalJobModalInstanceCtrl {
  constructor($filter, $translate, IP, $uibModalInstance, appConfig, $http, data, Notifications, Utils) {
    const $ctrl = this;
    // Set later to use local time for next job
    $ctrl.angular = angular;
    $ctrl.data = data;
    $ctrl.model = {};
    $ctrl.$onInit = () => {
      if (data.job) {
        $ctrl.model = angular.copy(data.job);
      }
      $ctrl.model.template = data.template.id;
    };

    $ctrl.fields = [
      {
        type: 'input',
        key: 'label',
        templateOptions: {
          label: $translate.instant('LABEL'),
        },
      },
      {
        className: 'row m-0',
        fieldGroup: [
          {
            className: 'col-xs-12 col-sm-6 px-0 pr-md-base',
            type: 'datepicker',
            key: 'start_date',
            templateOptions: {
              label: $translate.instant('START_DATE'),
              appendToBody: false,
            },
          },
          {
            className: 'col-xs-12 col-sm-6 px-0 pl-md-base',
            type: 'datepicker',
            key: 'end_date',
            templateOptions: {
              label: $translate.instant('END_DATE'),
              appendToBody: false,
            },
          },
        ],
      },
    ];

    $ctrl.createJob = () => {
      $ctrl.creatingJob = true;
      $http({
        url: appConfig.djangoUrl + 'appraisal-jobs/',
        method: 'POST',
        data: $ctrl.model,
      })
        .then(() => {
          $ctrl.creatingJob = false;
          Notifications.add($translate.instant('ARCHIVE_MAINTENANCE.JOB_CREATED'), 'success');
          $uibModalInstance.close($ctrl.data);
        })
        .catch(() => {
          $ctrl.creatingJob = false;
        });
    };
    $ctrl.runningJob = false;
    $ctrl.createJobAndStart = () => {
      $ctrl.runningJob = true;
      $http({
        url: appConfig.djangoUrl + 'appraisal-jobs/',
        method: 'POST',
        data: $ctrl.model,
      })
        .then(response => {
          $http({
            url: appConfig.djangoUrl + 'appraisal-jobs/' + response.data.id + '/run/',
            method: 'POST',
          })
            .then(() => {
              $ctrl.runningJob = false;
              Notifications.add($translate.instant('ARCHIVE_MAINTENANCE.JOB_RUNNING'), 'success');
              $uibModalInstance.close($ctrl.data);
            })
            .catch(() => {
              $ctrl.runningJob = false;
            });
        })
        .catch(() => {
          $ctrl.runningJob = false;
        });
    };

    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
