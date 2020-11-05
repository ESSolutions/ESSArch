export default class ExportNodeModalInstanceCtrl {
  constructor($translate, $uibModalInstance, data, $http, appConfig, $rootScope, $window, $sce) {
    const $ctrl = this;
    $ctrl.data = data;
    $ctrl.exportOptions = [];
    $ctrl.options = {};
    $ctrl.model = {option: 'email'};

    let getExportOptions = (node) => {
      $ctrl.exportOptions = [{name: $translate.instant('ACCESS.SEND_AS_EMAIL'), value: 'email'}];
      $ctrl.exportOptions.push({name: $translate.instant('ACCESS.EXPORT_OMEKA'), value: 'omeka'});
      if (node._index === 'archive') {
        $ctrl.exportOptions.push({name: $translate.instant('ACCESS.CREATE_LABELS'), value: 'labels'});
        $ctrl.exportOptions.push({name: $translate.instant('ACCESS.EXPORT_ARCHIVE'), value: 'archive'});
      }
      return $ctrl.exportOptions;
    };

    $ctrl.getOmekaCollections = function (search) {
      return $http({
        method: 'GET',
        url: appConfig.djangoUrl + 'search/omeka_api/collections/',
      }).then(function (response) {
        $ctrl.options.collections = [];
        response.data.forEach(function (col) {
          console.log('COLLECTION ID', col.id);
          col.element_texts.forEach(function (element_text) {
            console.log('element_text', element_text);
            if (element_text.element.name === 'Title') {
              console.log('title', element_text.text, col.id);
              $ctrl.options.collections.push({full_name: element_text.text, id: col.id});
            }
          });
        });
        return $ctrl.options.collections;
      });
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
      {
        type: 'uiselect',
        key: 'collection',
        templateOptions: {
          required: true,
          options: function () {
            return $ctrl.options.collections;
          },
          valueProp: 'id',
          labelProp: 'full_name',
          placeholder: $translate.instant('ACCESS.COLLECTION'),
          label: $translate.instant('ACCESS.COLLECTION'),
          appendToBody: false,
          refresh: function (search) {
            return $ctrl.getOmekaCollections(search);
          },
        },
        hideExpression: function ($viewValue, $modelValue, scope) {
          return scope.model.option !== 'omeka';
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

    let exportOmeka = (node, includeDescendants, collection) => {
      $ctrl.exporting = true;
      return $http({
        method: 'POST',
        url: appConfig.djangoUrl + 'search/' + node.id + '/export-to-omeka/',
        data: {
          include_descendants: includeDescendants,
          collection_id: collection,
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

    let exportxml2pdf = (node) => {
      const showFile = $sce.trustAsResourceUrl(appConfig.djangoUrl + 'search/' + node._id + '/xml2pdf/');
      $window.open(showFile, '_blank');
      $uibModalInstance.close();
    };

    $ctrl.export = (option) => {
      if (option) {
        if (option === 'email') {
          exportEmail(data.node, $ctrl.model.include_descendants);
        } else if (option === 'labels') {
          exportLabels(data.node);
        } else if (option === 'omeka') {
          exportOmeka(data.node, $ctrl.model.include_descendants, $ctrl.model.collection);
        } else if (option === 'archive') {
          exportArchive(data.node);
        } else if (option === 'xml2pdf') {
          exportxml2pdf(data.node);
        }
      }
    };
    $ctrl.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
