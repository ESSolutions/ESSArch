export default class ConversionSpecCtrl {
  constructor($http, $translate, appConfig) {
    let vm = this;
    vm.newSpec = {tool: null, path: null};
    vm.tool = null;
    vm.tools = [];
    vm.toolData = {};
    vm.toolDataForm = [];

    vm.getTools = search => {
      return $http.get(appConfig.djangoUrl + 'conversion-tools/', {params: {search, pager: 'none'}}).then(response => {
        response.data.map(x => {
          return {name: x.name, fullItem: x};
        });
        vm.tools = response.data;
        return response.data;
      });
    };

    vm.baseSpecFields = [
      {
        type: 'input',
        key: 'path',
        templateOptions: {
          label: $translate.instant('PATH'),
        },
      },
      {
        type: 'uiselect',
        key: 'tool',
        templateOptions: {
          options: function() {
            return vm.tools;
          },
          valueProp: 'name',
          labelProp: 'name',
          onChange: newVal => {
            vm.toolDataForm = vm.tools.filter(x => x.name === newVal)[0].form;
          },
          placeholder: $translate.instant('ARCHIVE_MAINTENANCE.TOOL'),
          label: $translate.instant('ARCHIVE_MAINTENANCE.TOOL'),
          appendToBody: false,
          refresh: function(search) {
            if (angular.isUndefined(search) || search === null || search === '') {
              search = '';
            }
            return vm.getTools(search).then(function() {
              this.options = vm.tools;
              return vm.tools;
            });
          },
        },
      },
    ];

    vm.addSpecification = function() {
      if (vm.specification === null || vm.specification === []) {
        vm.specification = {};
      }
      if (vm.newSpec.path) {
        vm.specification[vm.newSpec.path] = {
          tool: angular.copy(vm.newSpec.tool),
          options: angular.copy(vm.toolData),
        };
        vm.newSpec = {
          path: '',
          tool: null,
        };
        vm.toolData = {};
        vm.toolDataForm = [];
      }
    };

    vm.deleteSpecification = function(key) {
      delete vm.specification[key];
    };
  }
}
