export default class StorageMigrationModalInstanceCtrl {
  constructor(
    $uibModalInstance,
    data,
    $http,
    appConfig,
    $translate,
    $log,
    EditMode,
    $scope,
    $uibModal,
    listViewService,
    $q
  ) {
    const $ctrl = this;
    $ctrl.data = data;
    $ctrl.migration = {};
    $ctrl.itemsPerPage = 10;
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
        $ctrl.migration.policy = data.policy;
      });
      EditMode.enable();
    };

    const parseMethods = methods => {
      const methodTranslation = $translate.instant('STORAGE_METHOD');
      const targetTranslation = $translate.instant('STORAGE_TARGET');

      return methods.map(x => {
        let temp = x.storage_method_target_relations.filter(relation => {
          return relation.status === 1;
        });
        let enabledTarget = {name: null, id: null};
        if (temp.length > 0) {
          enabledTarget = temp[0];
        }
        const methodWithTarget = `
        <div class="method-target-result-item">
          <b>${methodTranslation}:</b> ${x.name}<br />
          <b>${targetTranslation}:</b> ${enabledTarget.name}
        </div>
        `;
        return {
          methodWithTarget,
          id: enabledTarget.storage_method,
        };
      });
    };

    let methods = [];
    const getMethods = search => {
      let params = {policy: data.policy, page: 1, page_size: 10, search, has_enabled_target: true};
      return $http.get(appConfig.djangoUrl + 'storage-methods/', {params}).then(response => {
        methods = parseMethods(response.data);
        return methods;
      });
    };

    let tempModel = {};

    $ctrl.fields = [
      {
        type: 'input',
        key: 'temp_path',
        templateOptions: {
          label: $translate.instant('TEMPPATH'),
        },
      },
      {
        type: 'input',
        key: 'purpose',
        templateOptions: {
          label: $translate.instant('PURPOSE'),
        },
      },
      {
        type: 'checkbox',
        key: 'migrate_all',
        templateOptions: {
          label: $translate.instant('MIGRATE_ALL_METHODS'),
        },
        defaultValue: true,
        model: tempModel,
        expressionProperties: {
          'templateOptions.onChange': function($viewValue, $modelValue, scope) {
            if ($modelValue === true) {
              delete $ctrl.migration.storage_methods;
            }
          },
        },
      },
      {
        key: 'storage_methods',
        type: 'uiselect',
        templateOptions: {
          label: $translate.instant('STORAGE_METHODS'),
          labelProp: 'methodWithTarget',
          multiple: true,
          valueProp: 'id',
          optionsFunction: function() {
            return methods;
          },
          appendToBody: false,
          refresh: function(search) {
            return getMethods(search);
          },
        },
        hideExpression: ($viewValue, $modelValue, scope) => {
          return tempModel.migrate_all;
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
          EditMode.disable();
          $uibModalInstance.close(response);
        })
        .catch(response => {
          $ctrl.migrating = false;
        });
    };

    $ctrl.preview = () => {
      return $uibModal
        .open({
          animation: true,
          ariaLabelledBy: 'modal-title',
          ariaDescribedBy: 'modal-body',
          templateUrl: 'static/frontend/views/storage_migration_preview_modal.html',
          controller: 'StorageMigrationPreviewModalInstanceCtrl',
          controllerAs: '$ctrl',
          size: 'lg',
          resolve: {
            data: function() {
              return {
                policy: data.policy,
                storage_methods: $ctrl.migration.storage_methods,
                information_packages: data.ips.map(x => x.id),
              };
            },
          },
        })
        .result.then(
          function(data) {
            return data;
          },
          function() {}
        );
    };

    $ctrl.cancel = function() {
      EditMode.disable();
      $uibModalInstance.dismiss('cancel');
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
