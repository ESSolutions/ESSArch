export default class ValidationCtrl {
  constructor($scope, $rootScope, appConfig, $translate, $http, $timeout, $uibModal) {
    const vm = this;
    vm.flowOptions = {};
    vm.options = {validators: []};
    vm.fields = $scope.mockedValidations;
    vm.activeTab = 'validation0';
    vm.purposeField = [
      {
        key: 'purpose',
        type: 'input',
        templateOptions: {
          label: $translate.instant('PURPOSE'),
        },
      },
    ];

    let tabNumber = 0;
    vm.validations = [
      {
        id: 0,
        label: $translate.instant('VALIDATION') + ' 1',
        validator: null,
        data: {},
      },
    ];
    vm.currentValidation = vm.validations[0];
    vm.updateValidatorForm = validation => {
      vm.currentValidation = validation;
      if (validation.validator) {
        vm.fields = validation.validator.form;
      } else {
        vm.fields = [];
      }
    };

    vm.getValidators = function(search) {
      return $http({
        url: appConfig.djangoUrl + 'validators/',
        method: 'GET',
        params: {search: search},
      }).then(function(response) {
        let validators = [];
        Object.keys(response.data).forEach(key => {
          validators.push(angular.extend(response.data[key], {name: key}));
        });
        vm.options.validators = validators;
        return vm.options.validators;
      });
    };

    vm.addValidator = () => {
      tabNumber++;
      let val = {
        id: tabNumber,
        label: $translate.instant('VALIDATION') + ' ' + (tabNumber + 1),
        validator: null,
        data: {},
      };
      vm.validations.push(val);
      $timeout(() => {
        vm.activeTab = 'validation' + tabNumber;
        vm.updateValidatorForm(val);
      });
    };

    vm.removeValidationModal = validation => {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_validation_modal.html',
        scope: $scope,
        controller: 'RemoveValidationModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            validation,
          },
        },
      });
      modalInstance.result.then(
        () => {
          vm.validations.forEach((x, index, array) => {
            if (x.id === validation.id) {
              array.splice(index, 1);
              tabNumber--;
            }
          });
        },
        function() {}
      );
    };

    vm.startValidation = () => {
      if (vm.form.$invalid) {
        vm.form.$setSubmitted();
        return;
      }
      let validations = vm.validations.filter(a => {
        return a.validator !== null;
      });
      if (validations.length > 0) {
        vm.validations = validations;
      }
      if (!angular.isUndefined(vm.flowOptions.purpose) && vm.flowOptions.purpose === '') {
        delete vm.flowOptions.purpose;
      }
      let data = angular.extend(vm.flowOptions, {
        information_package: vm.ip.id,
        validators: vm.validations.map(x => {
          let item = x.data;
          item.name = x.validator.name;
          return item;
        }),
      });
      $http.post(appConfig.djangoUrl + 'validator-workflows/', data).then(() => {
        $rootScope.$broadcast('REFRESH_LIST_VIEW', {});
      });
    };
  }
}
