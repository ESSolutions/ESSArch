export default class ConversionSpecCtrl {
  constructor($scope, $http, $translate, appConfig, $uibModal, $log) {
    let vm = this;
    $scope.angular = angular;
    vm.newSpec = {tool: null, path: null};
    vm.tool = null;
    vm.tools = [];
    vm.toolData = {};
    vm.toolDataForm = [];

    vm.getTools = (search) => {
      return $http
        .get(appConfig.djangoUrl + 'action-tools/', {params: {search, pager: 'none'}})
        .then((response) => {
          response.data.map((x) => {
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
          options: function () {
            return vm.tools;
          },
          valueProp: 'name',
          labelProp: 'name',
          onChange: (newVal) => {
            vm.toolDataForm = vm.tools.filter((x) => x.name === newVal)[0].form;
          },
          placeholder: $translate.instant('ARCHIVE_MAINTENANCE.TOOL'),
          label: $translate.instant('ARCHIVE_MAINTENANCE.TOOL'),
          appendToBody: false,
          refresh: function (search) {
            if (angular.isUndefined(search) || search === null || search === '') {
              search = '';
            }
            return vm.getTools(search).then(function () {
              this.options = vm.tools;
              return vm.tools;
            });
          },
        },
      },
    ];

    vm.addSpecification = function () {
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

    vm.removeSpecification = function (key) {
      delete vm.specification[key];
    };

    vm.specificationItemModal = (key, value) => {
      let specItem = angular.extend(
        {
          path: key,
        },
        value
      );
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/specification_item_modal.html',
        controller: 'SpecificationItemModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'md',
        resolve: {
          data: {
            specItem,
          },
        },
      });
      modalInstance.result.then(
        function (data) {},
        function () {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.removeSpecificationItemModal = (key, value) => {
      let specItem = angular.extend(
        {
          path: key,
        },
        value
      );
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_specification_item_modal.html',
        controller: 'SpecificationItemModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'md',
        resolve: {
          data: {
            specItem,
          },
        },
      });
      modalInstance.result
        .then(() => {
          vm.removeSpecification(key);
        })
        .catch(() => {
          $log.info('modal-component dismissed at: ' + new Date());
        });
    };
  }
}
