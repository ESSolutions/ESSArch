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
    $ctrl.ip = null;
    $ctrl.model = {package_file_pattern: []};
    $ctrl.fullIpAppraisal = true;

    $ctrl.$onInit = () => {
      if (data.appraisal) {
        $ctrl.model = angular.copy(data.appraisal);
        if ($ctrl.model.package_file_pattern && $ctrl.model.package_file_pattern.length > 0) {
          $ctrl.fullIpAppraisal = false;
        }
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

    $ctrl.path = '';
    $ctrl.addPath = function(path) {
      if (path.length > 0) {
        $ctrl.model.package_file_pattern.push(path);
      }
      $ctrl.path = '';
    };
    $ctrl.removePath = function(path) {
      $ctrl.model.package_file_pattern.splice($ctrl.model.package_file_pattern.indexOf(path), 1);
    };
    $ctrl.appraisalTemplate = null;
    $ctrl.create = function() {
      $ctrl.addingTemplate = true;
      if ($ctrl.createForm.$invalid) {
        $ctrl.createForm.$setSubmitted();
        return;
      }
      if ($ctrl.fullIpAppraisal) {
        $ctrl.model.package_file_pattern = [];
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
      if ($ctrl.fullIpAppraisal) {
        $ctrl.model.package_file_pattern = [];
      }
      if ($ctrl.createForm.$invalid) {
        $ctrl.createForm.$setSubmitted();
        return;
      }
      $http({
        url: appConfig.djangoUrl + 'appraisal-templates/' + template.id + '/',
        method: 'PATCH',
        data: $ctrl.model,
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
