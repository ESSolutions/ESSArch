export default class IpAppraisalJobModalInstanceCtrl {
  constructor($uibModalInstance, $translate, data, $http, appConfig, Search) {
    const $ctrl = this;
    $ctrl.model = {};
    $ctrl.options = {
      jobs: [],
    };
    $ctrl.data = data;

    $ctrl.getJobs = search => {
      return $http
        .get(appConfig.djangoUrl + 'appraisal-jobs/', {params: {search, status: 'PENDING'}})
        .then(response => {
          response.data.forEach(x => {
            x.labelProp = x.label && x.label !== '' ? x.label : x.id;
          });
          $ctrl.options.jobs = response.data;
          return response.data;
        });
    };

    $ctrl.fields = [
      {
        type: 'uiselect',
        key: 'job',
        templateOptions: {
          options: function() {
            return $ctrl.options.jobs;
          },
          valueProp: 'id',
          labelProp: 'labelProp',
          required: true,
          placeholder: $translate.instant('ARCHIVE_MAINTENANCE.APPRAISAL_JOB'),
          label: $translate.instant('ARCHIVE_MAINTENANCE.APPRAISAL_JOB'),
          appendToBody: false,
          refresh: function(search) {
            if (angular.isUndefined(search) || search === null || search === '') {
              search = '';
            }
            return $ctrl.getJobs(search).then(function() {
              this.options = $ctrl.options.jobs;
              return $ctrl.options.jobs;
            });
          },
        },
      },
    ];

    $ctrl.addToJob = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.adding = true;

      $http
        .patch(appConfig.djangoUrl + 'appraisal-jobs/' + $ctrl.model.job + '/information-packages/', {
          information_packages: data.ips.map(x => x.id),
        })
        .then(() => {
          $ctrl.adding = false;
          $uibModalInstance.close();
        })
        .catch(() => {
          $ctrl.adding = false;
        });
    };

    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
