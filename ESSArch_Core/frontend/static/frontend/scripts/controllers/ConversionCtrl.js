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
    var dianaaudiocontext = null;
    vm.showProfiles = false;

    vm.profileChosen = null;

    vm.profile = [];
    const ipToSearch = 'a44ad659-07f2-420c-aa80-f2d55df99970';

    vm.$onInit = function () {
      vm.profilesLoading = true;

      $http({
        url: appConfig.djangoUrl + 'profiles/',
        method: 'GET',
        params: {pager: 'none'},
      })
        .then(function (response) {
          const pdata = response.data;
          var profile = null;
          for (var j = 0; j < pdata.length; j++) {
            if (pdata[j].profile_type.includes('validation')) {
              profile = {
                id: pdata[j].id,
                name: pdata[j].name,
              };

              profilelist.push(profile);
            }
          }

          vm.profilesLoading = false;
        })
        .catch(() => {
          vm.profilesLoading = false;
        });

      vm.contextLoading = true;
      $http({
        url: appConfig.djangoUrl + 'profiles/450fcd19-d798-4e04-b392-575490103284/',
        method: 'GET',
        params: {pager: 'none'},
      })
        .then(function (response) {
          const pdata = response.data;
          dianaaudiocontext = pdata.specification.mediaconch[0].context;
          vm.contextLoading = false;
        })
        .catch(() => {
          vm.contextLoading = false;
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

    vm.arrlist = [
      {
        userid: 1,
        name: 'Diana Video',
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

    vm.getTFromREST = function (information_package) {
      var tids = [];
      return $http({
        url: appConfig.djangoUrl + 'tasks/',
        method: 'GET',
        params: {pager: 'none', information_package: information_package},
      }).then(function (response) {
        const tdata = response.data;
        for (var i = 0; i < tdata.length; i++) {
          if (tdata[i].information_package == information_package && !angular.equals([], tdata[i].args)) {
            tids.push(tdata[i]);
          }
        }
        return tids;
      });
    };

    vm.getValidationFromREST = function (task) {
      var fname = '';
      return $http({
        url: appConfig.djangoUrl + 'validations/',
        method: 'GET',
        params: {pager: 'none', task},
      }).then(function (response) {
        const vdata = response.data;

        return vdata;
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

    $scope.SelectedRow = function (selectedProfile) {
      console.log('item selected');
      console.log(selectedProfile);
      vm.profileChosen = selectedProfile;
      //vm.profilesLoading = true;

      $http({
        url: appConfig.djangoUrl + 'externalTool-description/',
        method: 'GET',
        params: {pager: 'none'},
      })
        .then(function (response) {
          const pdata = response.data;
          /*
          var profile = null;
          for (var j = 0; j < pdata.length; j++) {
            
            if (pdata[j].profile_type.includes('validation')) {
              profile = {
                id: pdata[j].id,
                name: pdata[j].name,
              };

              profilelist.push(profile);
            }
            
          }
*/
          console.log(pdata);
          for (var j = 0; j < pdata.length; j++) {
            console.log(pdata[j].actionTool.name);
          }
          //vm.profilesLoading = false;
        })
        .catch(() => {
          //vm.profilesLoading = false;
        });
    };
    vm.startConversion = () => {
      console.log('vm.profileChosen');
      console.log(vm.profileChosen);

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
  }
}
