export default class ExportNodeModalInstanceCtrl {
  constructor($translate, $uibModalInstance, data, $http, appConfig, $rootScope, $window, $sce) {
    const $ctrl = this;
    $ctrl.data = data;
    $ctrl.exportOptions = [];
    $ctrl.model = {option: 'email'};

    let getExportOptions = (node) => {
      $ctrl.exportOptions = [{name: $translate.instant('ACCESS.SEND_AS_EMAIL'), value: 'email'}];
      if (node._index === 'archive') {
        $ctrl.exportOptions.push({name: $translate.instant('ACCESS.CREATE_LABELS'), value: 'labels'});
        $ctrl.exportOptions.push({name: $translate.instant('ACCESS.EXPORT_ARCHIVE'), value: 'archive'});
      }
      return $ctrl.exportOptions;
    };

    $ctrl.fields = [
      {
        type: 'uiselect',
        key: 'option',
        templateOptions: {
          required: true,
          options: function () {
            return $ctrl.exportOptions;
          },
          valueProp: 'value',
          labelProp: 'name',
          label: $translate.instant('ACCESS.EXPORT_OPTION'),
          appendToBody: false,
          refresh: function (search) {
            return getExportOptions(data.node);
          },
        },
      },
      {
        type: 'checkbox',
        key: 'include_descendants',
        templateOptions: {
          label: $translate.instant('ACCESS.INCLUDE_DESCENDANT_NODES'),
          trueValue: true,
          falseValue: undefined,
        },
        defaultValue: false,
        hideExpression: function ($viewValue, $modelValue, scope) {
          return scope.model.option !== 'email';
        },
      },
    ];

    let exportEmail = (node, includeDescendants) => {
      $ctrl.exporting = true;
      return $http({
        method: 'POST',
        url: appConfig.djangoUrl + 'search/' + node.id + '/send-as-email/',
        data: {
          include_descendants: includeDescendants,
        },
      })
        .then(() => {
          $ctrl.exporting = false;
          $uibModalInstance.close();
        })
        .catch(() => {
          $ctrl.exporting = false;
        });
    };

    let exportLabels = (node) => {
      const showFile = $sce.trustAsResourceUrl(appConfig.djangoUrl + 'search/' + node._id + '/label/');
      $window.open(showFile, '_blank');
      $uibModalInstance.close();
    };

    let exportArchive = (node) => {
      const showFile = $sce.trustAsResourceUrl(appConfig.djangoUrl + 'search/' + node._id + '/export/');
      $window.open(showFile, '_blank');
      $uibModalInstance.close();
    };

    $ctrl.export = (option) => {
      if (option) {
        if (option === 'email') {
          exportEmail(data.node, $ctrl.model.include_descendants);
        } else if (option === 'labels') {
          exportLabels(data.node);
        } else if (option === 'archive') {
          exportArchive(data.node);
        }
      }
    };
    $ctrl.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
