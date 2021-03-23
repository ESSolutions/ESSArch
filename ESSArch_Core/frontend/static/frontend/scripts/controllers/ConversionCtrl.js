export default class ConversionCtrl {
  constructor($scope, $rootScope, appConfig, $translate, $http, $timeout, $uibModal) {
    const vm = this;
    vm.flowOptions = {};
    vm.options = {converters: []};
    vm.fields = $scope.mockedConversions;
    vm.activeTab = 'conversion0';
    vm.profiles = [];
    vm.profilelist = [];
    var profilelist = [];
    vm.showProfiles = false;
    vm.selectedProfile = null;
    vm.profilespec = [];
    vm.response = {text: [], path: []};
    vm.savedWorkflow = '';

    vm.profileChosen = null;

    vm.profile = [];

    vm.$onInit = function () {
      vm.profilesLoading = true;

      $http({
        url: appConfig.djangoUrl + 'profiles/',
        method: 'GET',
        params: {pager: 'none'},
      })
        .then(function (response) {
          const pdata = response.data;
          for (var j = 0; j < pdata.length; j++) {
            if (pdata[j].profile_type.includes('action_workflow')) {
              profilelist.push(pdata[j]);
            }
          }
          vm.profilelist = profilelist;
          vm.profilesLoading = false;
        })
        .catch(() => {
          vm.profilesLoading = false;
        });
    };

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
    vm.conversions = [
      {
        id: 0,
        name: '1',
        converter: null,
        data: {},
      },
    ];

    vm.currentConversion = vm.conversions[0];
    vm.updateConverterForm = (conversion) => {
      vm.currentConversion = conversion;
      if (conversion.converter) {
        vm.fields = conversion.converter.form;
      } else {
        vm.fields = [];
      }
    };

    vm.getConverters = function (search) {
      return $http({
        url: appConfig.djangoUrl + 'action-tools/',
        method: 'GET',
        params: {search: search, pager: 'none'},
      }).then(function (response) {
        vm.options.converters = response.data.map((converter) => {
          return converter;
        });
        return vm.options.converters;
      });
    };

    vm.addConverter = () => {
      tabNumber++;
      let val = {
        id: tabNumber,
        name: tabNumber + 1,
        validator: null,
        data: {},
      };
      vm.conversions.push(val);
      $timeout(() => {
        vm.activeTab = 'conversion' + tabNumber;
        vm.updateConverterForm(val);
      });
    };

    vm.deleteFromWorkflow = (value) => {
      var index = vm.profilespec.indexOf(value);
      vm.profilespec.splice(index, 1);
    };

    vm.actionDetailsModal = (value) => {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/action_details_modal.html',
        scope: $scope,
        controller: 'ActionDetailsModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            value,
          },
        },
      });
      modalInstance.result.then(
        () => {},
        function () {}
      );
    };

    vm.saveWorkflowModal = () => {
      var workflow = vm.conversions;
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/save_workflow_modal.html',
        scope: $scope,
        controller: 'SaveWorkflowModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            workflow,
          },
        },
      });
      modalInstance.result.then(
        (result) => {
          if (vm.form.$invalid) {
            vm.form.$setSubmitted();
            return;
          }
          let conversions = vm.conversions.filter((a) => {
            return a.conversion !== null;
          });
          if (conversions.length > 0) {
            vm.conversions = conversions;
          }
          if (!angular.isUndefined(vm.flowOptions.purpose) && vm.flowOptions.purpose === '') {
            delete vm.flowOptions.purpose;
          }
          let data = angular.extend(vm.flowOptions, {
            actions: vm.conversions.map((x) => {
              let data = angular.copy(x.data);
              delete data.path;
              return {
                name: x.converter.name,
                options: data,
                path: x.data.path,
              };
            }),
            action_workflow_name: result.action_workflow_name,
            action_workflow_status: result.action_workflow_status,
          });

          const id = vm.baseUrl === 'workareas' ? vm.ip.workarea[0].id : vm.ip.id;
          const baseUrl = vm.baseUrl === 'workareas' ? 'workarea-entries' : vm.baseUrl;
          $http.post(appConfig.djangoUrl + baseUrl + '/' + id + '/actiontool_save/', data).then(() => {
            $rootScope.$broadcast('REFRESH_LIST_VIEW', {});
            vm.savedWorkflow = 'Saved workflow ' + result.action_workflow_name;
          });
        },
        function () {}
      );
    };

    vm.removeConversionModal = (conversion) => {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_conversion_modal.html',
        scope: $scope,
        controller: 'RemoveConversionModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            conversion,
          },
        },
      });
      modalInstance.result.then(
        () => {
          vm.conversions.forEach((x, index, array) => {
            if (x.id === conversion.id) {
              array.splice(index, 1);
              tabNumber--;
              $timeout(() => {
                vm.activeTab = 'conversion' + tabNumber;
              });
            }
          });
        },
        function () {}
      );
    };

    vm.fetchClick = () => {
      $http({
        url: appConfig.djangoUrl + 'profiles/' + vm.selectedProfile.id + '/',
        method: 'GET',
        params: {pager: 'none'},
      })
        .then(function (response) {
          var profilespec = response.data.specification[0].children;
          for (var i = 0; i < profilespec.length; i++) {
            vm.response.text.push(profilespec[i].args[0]);
            vm.response.path.push(profilespec[i].args[1]);
          }
          vm.profilespec = profilespec;
        })
        .catch(() => {
          console.log('Caught error');
        });
    };

    vm.SelectedRow = function (selectedProfile) {
      vm.selectedProfile = selectedProfile;
      vm.conversions;
    };

    vm.startConversion = () => {
      if (vm.form.$invalid) {
        vm.form.$setSubmitted();
        return;
      }
      let conversions = vm.conversions.filter((a) => {
        return a.conversion !== null;
      });
      if (conversions.length > 0) {
        vm.conversions = conversions;
      }
      if (!angular.isUndefined(vm.flowOptions.purpose) && vm.flowOptions.purpose === '') {
        delete vm.flowOptions.purpose;
      }
      let data = angular.extend(vm.flowOptions, {
        actions: vm.conversions.map((x) => {
          let data = angular.copy(x.data);
          delete data.path;
          return {
            name: x.converter.name,
            options: data,
            path: x.data.path,
          };
        }),
      });

      const id = vm.baseUrl === 'workareas' ? vm.ip.workarea[0].id : vm.ip.id;
      const baseUrl = vm.baseUrl === 'workareas' ? 'workarea-entries' : vm.baseUrl;
      $http.post(appConfig.djangoUrl + baseUrl + '/' + id + '/actiontool/', data).then(() => {
        $rootScope.$broadcast('REFRESH_LIST_VIEW', {});
      });
    };

    vm.startPresetConversion = () => {
      if (vm.form.$invalid) {
        vm.form.$setSubmitted();
        return;
      }
      let conversions = vm.conversions.filter((a) => {
        return a.conversion !== null;
      });
      if (conversions.length > 0) {
        vm.conversions = conversions;
      }
      if (!angular.isUndefined(vm.flowOptions.purpose) && vm.flowOptions.purpose === '') {
        delete vm.flowOptions.purpose;
      }
      let datapreset = null;
      let datacustom = null;
      if (vm.profilespec.length > 0) {
        datapreset = angular.extend(vm.flowOptions, {
          actions: vm.profilespec.map((x) => {
            return {
              name: x.args[0],
              options: x.args[2],
              path: x.args[1],
            };
          }),
        });
      }

      if (vm.conversions.length > 0) {
        if (vm.conversions[0].converter !== null) {
          if (vm.conversions[0].converter.name !== null) {
            try {
              datacustom = angular.extend(vm.flowOptions, {
                actions: vm.conversions.map((x) => {
                  let data = angular.copy(x.data);
                  delete data.path;
                  return {
                    name: x.converter.name,
                    options: data,
                    path: x.data.path,
                  };
                }),
              });
            } catch (e) {
              console.log('Exited with error');
              console.log(e);
            }
          }
        }
      }
      let data = null;
      const id = vm.baseUrl === 'workareas' ? vm.ip.workarea[0].id : vm.ip.id;
      const baseUrl = vm.baseUrl === 'workareas' ? 'workarea-entries' : vm.baseUrl;
      if (datacustom) {
        data = datacustom;
        $http.post(appConfig.djangoUrl + baseUrl + '/' + id + '/actiontool/', data).then(() => {
          $rootScope.$broadcast('REFRESH_LIST_VIEW', {});
        });
      }
      if (datapreset) {
        data = datapreset;
        $http.post(appConfig.djangoUrl + baseUrl + '/' + id + '/actiontool/', data).then(() => {
          $rootScope.$broadcast('REFRESH_LIST_VIEW', {});
        });
      }
    };
  }
}
