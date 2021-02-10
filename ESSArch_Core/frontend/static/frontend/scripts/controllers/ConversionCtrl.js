export default class ConversionCtrl {
  constructor($scope, $rootScope, appConfig, $translate, $http, $timeout, $uibModal) {
    const vm = this;
    vm.flowOptions = {};
    vm.options = {converters: []};
    vm.fields = $scope.mockedConversions;
    vm.activeTab = 'conversion0';
    vm.validations = null;
    vm.tasks = null;
    var ip = null;
    vm.tool = null;
    vm.status = null;
    const taskids = [];
    vm.validations = null;
    vm.objectsshown = 3;

    vm.$onInit = function () {
      vm.validationsLoading = true;

      const activeip = vm.baseUrl === 'workareas' ? vm.ip.workarea[0].id : vm.ip.id;
      vm.getTFromREST(activeip)
        .then(function (tids) {
          const files = [];
          vm.tids = tids;
          $http({
            url: appConfig.djangoUrl + 'validations/',
            method: 'GET',
            params: {pager: 'none'},
          }).then(function (response) {
            const vdata = response.data;
            console.log(vdata);
            for (var i = 0; i < tids.length; i++) {
              for (var j = 0; j < vdata.length; j++) {
                if (vdata[j].task.includes(tids[i].id)) {
                  console.log('vdata: ');
                  console.log(vdata[j].id);
                  var validation = null;
                  if (vdata[j].passed == true) {
                    validation = {
                      id: vdata[j].id,
                      taskid: tids[i].id,
                      label: tids[i].label,
                      filename: vdata[j].filename,
                      passed: 'Success',
                      validator: vdata[j].validator,
                      time_started: vdata[j].time_started,
                    };
                  } else if (vdata[j].passed == false) {
                    validation = {
                      id: vdata[j].id,
                      taskid: tids[i].id,
                      label: tids[i].label,
                      filename: vdata[j].filename,
                      passed: 'Failure',
                      validator: vdata[j].validator,
                      time_started: vdata[j].time_started,
                    };
                  } else {
                    validation = {
                      id: vdata[j].id,
                      taskid: tids[i].id,
                      label: tids[i].label,
                      filename: vdata[j].filename,
                      passed: 'Unknown',
                      validator: vdata[j].validator,
                      time_started: vdata[j].time_started,
                    };
                  }

                  files.push(validation);
                }
              }
            }
            vm.validations = files;
          });
          vm.validationsLoading = false;
        })
        .catch(() => {
          vm.validationsLoading = false;
        });
    };

    vm.getTaskIDs = function (activeip) {
      var tarray = [];

      vm.validationsLoading = true;
      vm.getTFromREST(activeip)
        .then(function (tids) {
          tarray = tids;
        })
        .catch(() => {
          tarray = null;
        });

      return tarray;
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

    $scope.clickForModal = function(currentStepTask) {      
      $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/actionmodal.html',
        scope: $scope,
        controller: 'ActionModalCtrl',
        resolve: {
          currentStepTask
        },
      });
    }

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
  }
}
