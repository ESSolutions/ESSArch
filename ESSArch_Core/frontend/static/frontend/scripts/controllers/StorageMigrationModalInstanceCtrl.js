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
    let methods = [];
    let export_path = '';
    $ctrl.migration.export_path = '';
    let tempModel = {}; // Formly model for checkbox visibility

    $ctrl.$onInit = function () {
      if ($ctrl.data.ips == null && $ctrl.data.ip != null) {
        $ctrl.data.ips = [$ctrl.data.ip];
      }

      $ctrl.pageLoading = true;

      // Fetch paths
      $http.get(appConfig.djangoUrl + 'paths/', {params: {pager: 'none'}}).then((response) => {
        let temp = '';
        response.data.forEach((x) => {
          if (x.entity === 'temp') temp = x.value;
          else if (x.entity === 'export') export_path = x.value;
        });
        $ctrl.migration.temp_path = temp;
        export_path = export_path || temp;
        $ctrl.migration.policy = $ctrl.data.policy;
      });

      // Fetch storage methods
      let params = {policy: $ctrl.data.policy, page: 1, pager: 'none', has_enabled_target: true};
      $http.get(appConfig.djangoUrl + 'storage-methods/', {params}).then((response) => {
        methods = parseMethods(response.data);
        $ctrl.migration.storage_methods = methods.map((x) => x.id);
      });

      // -----------------------------
      // Fetch default checkbox parameters
      // -----------------------------
      $http.get(appConfig.djangoUrl + 'parameters/', {params: {pager: 'none'}}).then((response) => {
        let migrate_all_default = true; // fallback default
        let export_copy_default = false; // fallback default

        response.data.forEach((x) => {
          if (x.entity === 'migrate_all_default') migrate_all_default = x.value === 'true';
          if (x.entity === 'export_copy_default') export_copy_default = x.value === 'true';
        });

        // Apply defaults to tempModel
        tempModel.migrate_all = migrate_all_default;
        tempModel.export_copy = export_copy_default;

        // Preselect storage methods if migrate_all_default
        if (migrate_all_default && methods.length > 0) {
          $ctrl.migration.storage_methods = methods.map((x) => x.id);
        }

        // Set export path if export_copy_default
        if (export_copy_default && $ctrl.migration.export_path.length === 0) {
          $ctrl.migration.export_path = export_path;
        }
      });

      EditMode.enable();
    };

    const parseMethods = (methods) => {
      const methodTranslation = $translate.instant('STORAGE_METHOD');
      const targetTranslation = $translate.instant('STORAGE_TARGET');

      return methods.map((x) => {
        let temp = x.storage_method_target_relations.filter((relation) => relation.status === 1);
        let enabledTarget = {name: null, id: null};
        if (temp.length > 0) enabledTarget = temp[0];

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

    $ctrl.fields = [
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
        model: tempModel,
        templateOptions: {
          label: $translate.instant('MIGRATE_ALL_METHODS'),
        },
        expressionProperties: {
          'templateOptions.onChange': function ($viewValue, $modelValue, scope) {
            if ($modelValue && $ctrl.migration.storage_methods.length === 0) {
              $ctrl.migration.storage_methods = methods.map((x) => x.id);
            } else if (!$modelValue && $ctrl.migration.storage_methods.length !== 0) {
              $ctrl.migration.storage_methods = [];
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
          valueProp: 'id',
          multiple: true,
          optionsFunction: function () {
            return methods;
          },
          appendToBody: false,
        },
        hideExpression: () => tempModel.migrate_all === false,
      },
      {
        type: 'checkbox',
        key: 'export_copy',
        model: tempModel,
        templateOptions: {
          label: $translate.instant('EXPORT_COPY'),
        },
        expressionProperties: {
          'templateOptions.onChange': function ($viewValue, $modelValue, scope) {
            if ($modelValue && $ctrl.migration.export_path.length === 0) {
              $ctrl.migration.export_path = export_path;
            } else if (!$modelValue && $ctrl.migration.export_path.length !== 0) {
              $ctrl.migration.export_path = '';
            }
          },
        },
      },
      {
        type: 'input',
        key: 'export_path',
        templateOptions: {
          label: $translate.instant('EXPORTPATH'),
        },
        hideExpression: () => tempModel.export_copy === false,
      },
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

      let req_data = {};
      if ($ctrl.data.ips) {
        req_data = angular.extend(
          {
            information_packages: $ctrl.data.ips.map((x) => x.id),
          },
          $ctrl.migration
        );
      } else if ($ctrl.data.mediums) {
        req_data = angular.extend(
          {
            storage_mediums: $ctrl.data.mediums.map((x) => x.id),
          },
          $ctrl.migration
        );
      }

      $ctrl.migrating = true;
      return $http({
        method: 'POST',
        url: appConfig.djangoUrl + 'storage-migrations/',
        data: req_data,
      })
        .then((response) => {
          $ctrl.migrating = false;
          EditMode.disable();
          $uibModalInstance.close(response);
        })
        .catch((response) => {
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
            data: function () {
              if ($ctrl.data.ips) {
                return {
                  include_inactive_ips: $ctrl.data.include_inactive_ips,
                  missing_storage: $ctrl.data.missing_storage,
                  policy: $ctrl.data.policy,
                  storage_methods: $ctrl.migration.storage_methods,
                  information_packages: $ctrl.data.ips.map((x) => x.id),
                  export_path: $ctrl.migration.export_path,
                };
              } else if ($ctrl.data.mediums) {
                return {
                  include_inactive_ips: $ctrl.data.include_inactive_ips,
                  missing_storage: $ctrl.data.missing_storage,
                  policy: $ctrl.data.policy,
                  storage_methods: $ctrl.migration.storage_methods,
                  storage_mediums: $ctrl.data.mediums.map((x) => x.id),
                  export_path: $ctrl.migration.export_path,
                };
              }
            },
          },
        })
        .result.then(
          function (data) {
            return data;
          },
          function () {}
        );
    };

    $ctrl.cancel = function () {
      EditMode.disable();
      $uibModalInstance.dismiss('cancel');
    };

    $scope.$on('modal.closing', function (event, reason, closed) {
      if (
        ($ctrl.data.allow_close === null ||
          angular.isUndefined($ctrl.data.allow_close) ||
          $ctrl.data.allow_close !== true) &&
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
