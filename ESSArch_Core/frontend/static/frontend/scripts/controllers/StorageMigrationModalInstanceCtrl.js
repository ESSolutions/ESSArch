export default class StorageMigrationModalInstanceCtrl {
  constructor($uibModalInstance, data, $http, appConfig, $translate, $log) {
    var $ctrl = this;
    $ctrl.data = data;
    $ctrl.migration = {};
    $ctrl.$onInit = function() {
      if ($ctrl.data.ips == null) {
        $ctrl.data.ips = [$ctrl.data.ip];
      }
      $ctrl.pageLoading = true;
      $http.get(appConfig.djangoUrl + 'paths/', {params: {pager: 'none'}}).then(response => {
        $ctrl.pageLoading = false;
        let temp = '';
        response.data.forEach(x => {
          if (x.entity === 'temp') {
            temp = x.value;
          }
        });
        $ctrl.migration.temp_path = temp;
      });
    };

    $ctrl.fields = [
      {
        type: 'input',
        key: 'temp_path',
        templateOptions: {
          label: $translate.instant('TEMPPATH'),
        },
      },
    ];

    $ctrl.migrate = () => {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.migrating = true;
      return $http({
        method: 'POST',
        url: appConfig.djangoUrl + 'storage-migrations/',
        data: angular.extend(
          {
            information_packages: $ctrl.data.ips.map(x => {
              return x.id;
            }),
          },
          $ctrl.migration
        ),
      })
        .then(response => {
          $ctrl.migrating = false;
          $uibModalInstance.close(response);
        })
        .catch(response => {
          $ctrl.migrating = false;
        });
    };

    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
