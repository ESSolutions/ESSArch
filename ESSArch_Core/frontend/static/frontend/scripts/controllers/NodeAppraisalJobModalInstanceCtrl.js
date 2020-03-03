export default class NodeAppraisalJobModalInstanceCtrl {
  constructor($uibModalInstance, $translate, data, $http, appConfig, Search, Notifications) {
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

    $ctrl.addSearchToJob = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.adding = true;
      let promise;
      $http
        .get(appConfig.djangoUrl + 'search/', {
          params: angular.extend({add_to_appraisal: $ctrl.model.job}, data.search.filters),
        })
        .then(() => {
          $ctrl.adding = false;
          Notifications.add($translate.instant('ARCHIVE_MAINTENANCE.NODES_ADDED_TO_APPRAISAL_JOB'), 'success');
          $uibModalInstance.close();
        })
        .catch(e => {
          $ctrl.adding = false;
        });
    };

    $ctrl.addNodesToJob = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.adding = true;
      $http({
        method: 'PATCH',
        url: appConfig.djangoUrl + 'appraisal-jobs/' + $ctrl.model.job + '/tags/',
        data: {
          tags: data.nodes.map(x => x.tag),
        },
      })
        .then(() => {
          $ctrl.adding = false;
          Notifications.add($translate.instant('ARCHIVE_MAINTENANCE.NODES_ADDED_TO_APPRAISAL_JOB'), 'success');
          $uibModalInstance.close();
        })
        .catch(e => {
          $ctrl.adding = false;
        });
    };

    $ctrl.removeNode = node => {
      $ctrl.removing = true;
      $http({
        method: 'DELETE',
        url: appConfig.djangoUrl + 'appraisal-jobs/' + data.job.id + '/tags/',
        headers: {'Content-type': 'application/json'},
        data: {tags: [node.id]},
      })
        .then(() => {
          $ctrl.removing = false;
          Notifications.add($translate.instant('ARCHIVE_MAINTENANCE.NODE_REMOVED_FROM_APPRAISAL_JOB'), 'success');
          $uibModalInstance.close();
        })
        .catch(() => {
          $ctrl.removing = false;
        });
    };

    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
