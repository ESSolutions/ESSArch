export default class ConversionCtrl {
  constructor(
    $scope,
    $rootScope,
    appConfig,
    $translate,
    $http,
    $timeout,
    $uibModal,
    Notifications,
    $cacheFactory,
    $log
  ) {
    const vm = this;
    vm.flowOptions = {};
    vm.options = {converters: []};
    vm.fields = $scope.mockedConversions;
    vm.activeTab = 'conversion0';
    vm.profiles = [];
    vm.profilelist = [];
    var profilelist = [];
    vm.showProfiles = false;
    vm.profilespec = [];
    vm.addedActions = [];
    vm.response = {text: [], path: []};
    var addAction = {};

    vm.profileChosen = null;

    vm.profile = [];
    $scope.selectedProfile = {};
    $scope.selectedProfile = vm.profilelist[0];
    vm.cache = $cacheFactory.get('cacheId') || $cacheFactory('cacheId');

    vm.$onInit = function () {
      vm.getProfiles();

      if (vm.cache.get('ip.id') === vm.ip.id) {
        if (vm.cache.get('addedActions')) {
          vm.addedActions = vm.cache.get('addedActions');
        }
        if (vm.cache.get('profilespec')) {
          vm.profilespec = vm.cache.get('profilespec');
        }
        if (vm.cache.get('nameOfWorkflow')) {
          vm.nameOfWorkflow = vm.cache.get('nameOfWorkflow');
        }
      }

      vm.workflowActive = false;
    };

    vm.getProfiles = () => {
      vm.profilesLoading = true;

      $http({
        url: appConfig.djangoUrl + 'profiles/',
        method: 'GET',
        params: {pager: 'none'},
      })
        .then(function (response) {
          const pdata = response.data;
          profilelist = [];
          for (var j = 0; j < pdata.length; j++) {
            if (pdata[j].profile_type.includes('action_workflow')) {
              profilelist.push(pdata[j]);
            }
          }
          vm.profilelist = profilelist;
          vm.profilesLoading = false;
        })
        .catch(function (data) {
          Notifications.add(
            $translate.instant('CONVERSION_VIEW.ERROR_GET_PROFILES') + ' ' + data.statusText + '(' + data.status + ')',
            'error'
          );
          $log.error('Error getting profiles from server: ' + angular.toJson(data));
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
      })
        .then(function (response) {
          vm.options.converters = response.data.map((converter) => {
            return converter;
          });
          return vm.options.converters;
        })
        .catch(function (data) {
          Notifications.add(
            $translate.instant('CONVERSION_VIEW.ERROR_GET_ACTION_TOOLS') +
              ' ' +
              data.statusText +
              '(' +
              data.status +
              ')',
            'error'
          );
          $log.error('Error getting action tools from server: ' + angular.toJson(data));
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

    vm.put = function (key, value) {
      vm.cache.put(key, value);
    };

    vm.deleteFromWorkflow = (value) => {
      var index = vm.profilespec.indexOf(value);
      vm.profilespec.splice(index, 1);

      if (vm.profilespec.length < 1 && vm.addedActions.length < 1) {
        vm.profilespec = [];
        vm.addedActions = [];
        vm.updateCache();
        vm.workflowActive = false;
      }
    };

    vm.updateCache = function () {
      vm.put('selectedProfile', $scope.selectedProfile);
      if ($scope.selectedProfile) {
        vm.put('nameOfWorkflow', $scope.selectedProfile.name);
      } else {
        vm.put('nameOfWorkflow', '');
      }

      vm.put('profilespec', vm.profilespec);

      vm.put('addedActions', vm.addedActions);

      vm.put('ip.id', vm.ip.id);
    };

    vm.deleteAddedFromWorkflow = (value) => {
      if (vm.addedActions.length > 0) {
        var index = vm.addedActions.indexOf(value);
        vm.addedActions.splice(index, 1);

        if (vm.profilespec.length < 1 && vm.addedActions.length < 1) {
          vm.profilespec = [];
          vm.addedActions = [];
          vm.updateCache();
          vm.workflowActive = false;
        }
      }
      vm.updateCache();
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

    vm.saveAsWorkflowModal = () => {
      if (vm.profilespec.length > 0 || (vm.addedActions.length > 0 && vm.workflowActive)) {
        var workflow = null;
        var currentProfile = null;
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
            test: {
              currentProfile,
            },
          },
        });
        modalInstance.result.then(
          (result) => {
            let data = null;

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
            vm.flowOptions = {};
            let datapreset = null;
            let datanewactions = null;

            if (vm.profilespec.length > 0) {
              vm.flowOptions = {};
              datapreset = angular.extend(vm.flowOptions, {
                actions: vm.profilespec.map((x) => {
                  return {
                    name: x.args[0],
                    options: x.args[2],
                    path: x.args[1],
                  };
                }),
                action_workflow_name: result.action_workflow_name,
                action_workflow_status: result.action_workflow_status,
              });
            }

            if (vm.addedActions.length > 0) {
              vm.flowOptions = {};
              datanewactions = angular.extend(vm.flowOptions, {
                actions: vm.addedActions.map((x) => {
                  return {
                    name: x.name,
                    options: x.options,
                    path: x.path,
                  };
                }),
                action_workflow_name: result.action_workflow_name,
                action_workflow_status: result.action_workflow_status,
              });
            }

            if (vm.profilespec.length > 0 && vm.addedActions.length > 0) {
              datapreset.actions = datapreset.actions.concat(datanewactions.actions);
              data = datapreset;
            } else if (vm.addedActions.length > 0) {
              data = datanewactions;
            } else if (vm.profilespec.length > 0) {
              data = datapreset;
            }

            const id = vm.baseUrl === 'workareas' ? vm.ip.workarea[0].id : vm.ip.id;
            const baseUrl = vm.baseUrl === 'workareas' ? 'workarea-entries' : vm.baseUrl;
            $http
              .post(appConfig.djangoUrl + baseUrl + '/' + id + '/actiontool_save_as/', data)
              .then(() => {
                $rootScope.$broadcast('REFRESH_LIST_VIEW', {});
                Notifications.add('Saved workflow ' + result.action_workflow_name, 'success');
                vm.getProfiles();
              })
              .catch(function (data) {
                Notifications.add(
                  $translate.instant('CONVERSION_VIEW.ERROR_POST_WORKFLOW') +
                    ' ' +
                    data.statusText +
                    '(' +
                    data.status +
                    ')',
                  'error'
                );
                $log.error('Error posting workflow to server: ' + angular.toJson(data));
              });
          },
          function () {}
        );
      }
      vm.updateCache();
    };

    vm.cancelWorkflow = () => {
      vm.profilespec = [];
      vm.addedActions = [];
      $scope.selectedProfile = null;
      vm.updateCache();
    };

    vm.saveWorkflowModal = () => {
      if (vm.profilespec.length > 0 || (vm.addedActions.length > 0 && vm.workflowActive)) {
        var workflow = $scope.selectedProfile;
        var currentProfile = $scope.selectedProfile;
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
              currentProfile,
            },
          },
        });
        modalInstance.result.then(
          (result) => {
            let data = null;

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
            vm.flowOptions = {};
            let datapreset = null;
            let datanewactions = null;

            if (vm.profilespec.length > 0) {
              vm.flowOptions = {};
              datapreset = angular.extend(vm.flowOptions, {
                actions: vm.profilespec.map((x) => {
                  return {
                    name: x.args[0],
                    options: x.args[2],
                    path: x.args[1],
                  };
                }),
                action_workflow_name: result.action_workflow_name,
                action_workflow_status: result.action_workflow_status,
              });
            }

            if (vm.addedActions.length > 0) {
              vm.flowOptions = {};
              datanewactions = angular.extend(vm.flowOptions, {
                actions: vm.addedActions.map((x) => {
                  return {
                    name: x.name,
                    options: x.options,
                    path: x.path,
                  };
                }),
                action_workflow_name: result.action_workflow_name,
                action_workflow_status: result.action_workflow_status,
              });
            }

            if (vm.profilespec.length > 0 && vm.addedActions.length > 0) {
              datapreset.actions = datapreset.actions.concat(datanewactions.actions);
              data = datapreset;
            } else if (vm.addedActions.length > 0) {
              data = datanewactions;
            } else if (vm.profilespec.length > 0) {
              data = datapreset;
            }

            const id = vm.baseUrl === 'workareas' ? vm.ip.workarea[0].id : vm.ip.id;
            const baseUrl = vm.baseUrl === 'workareas' ? 'workarea-entries' : vm.baseUrl;
            $http
              .put(appConfig.djangoUrl + baseUrl + '/' + id + '/actiontool_save/', data)
              .then(() => {
                $rootScope.$broadcast('REFRESH_LIST_VIEW', {});
                Notifications.add('Saved workflow ' + result.action_workflow_name, 'success');
                vm.getProfiles();
              })
              .catch(function (data) {
                Notifications.add(
                  $translate.instant('CONVERSION_VIEW.ERROR_PUT_WORKFLOW') +
                    ' ' +
                    data.statusText +
                    '(' +
                    data.status +
                    ')',
                  'error'
                );
                $log.error('Error saving workflow update on server: ' + angular.toJson(data));
              });
          },
          function () {}
        );
      }
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
        url: appConfig.djangoUrl + 'profiles/' + $scope.selectedProfile.id + '/',
        method: 'GET',
        params: {pager: 'none'},
      })
        .then(function (response) {
          vm.profilespec = response.data.specification[0].children;
        })
        .then(function () {
          vm.nameOfWorkflow = $scope.selectedProfile.name;
          vm.updateCache();
        })
        .catch(function (data) {
          Notifications.add(
            $translate.instant('CONVERSION_VIEW.ERROR_GET_PROFILES') + ' ' + data.statusText + '(' + data.status + ')',
            'error'
          );
          $log.error('Error getting profiles from server: ' + angular.toJson(data));
        });

      vm.workflowActive = true;
    };

    vm.newToList = () => {
      let data = null;
      var action_name = null;
      var action_options = null;
      var action_path = null;

      if (vm.conversions.length > 0) {
        if (vm.conversions[0].converter !== null) {
          if (vm.conversions[0].converter.name !== null) {
            try {
              data = angular.extend(vm.flowOptions, {
                actions: vm.conversions.map((x) => {
                  data = angular.copy(x.data);
                  action_name = x.converter.name;
                  action_options = data;
                  action_path = x.data.path;
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
      addAction = {};

      addAction.name = action_name;
      addAction.options = action_options;
      addAction.path = action_path;
      addAction.conversions = vm.currentConversion;
      addAction.data = data;

      vm.addedActions.push(addAction);

      vm.updateCache();

      vm.workflowActive = true;
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
      let datanewactions = null;

      if (vm.profilespec.length > 0) {
        vm.flowOptions = {};
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

      if (vm.addedActions.length > 0) {
        vm.flowOptions = {};
        datanewactions = angular.extend(vm.flowOptions, {
          actions: vm.addedActions.map((x) => {
            return {
              name: x.name,
              options: x.options,
              path: x.path,
            };
          }),
        });
      }

      const id = vm.baseUrl === 'workareas' ? vm.ip.workarea[0].id : vm.ip.id;
      const baseUrl = vm.baseUrl === 'workareas' ? 'workarea-entries' : vm.baseUrl;

      if (datanewactions && datapreset) {
        $http({
          method: 'POST',
          url: appConfig.djangoUrl + baseUrl + '/' + id + '/actiontool/',
          data: datanewactions,
        })
          .then(() => {
            $http({
              method: 'POST',
              url: appConfig.djangoUrl + baseUrl + '/' + id + '/actiontool/',
              data: datapreset,
            });
          })
          .then(() => {
            vm.updateCache();
          })
          .then(() => {
            $rootScope.$broadcast('REFRESH_LIST_VIEW', {});
          })
          .catch(function (data) {
            Notifications.add(
              $translate.instant('CONVERSION_VIEW.ERROR_RUN_ACTIONS') +
                ' ' +
                data.statusText +
                '(' +
                data.status +
                ')',
              'error'
            );
            $log.error('Problem running actions. Error from server: ' + angular.toJson(data));
          });
      } else if (datapreset) {
        $http({
          method: 'POST',
          url: appConfig.djangoUrl + baseUrl + '/' + id + '/actiontool/',
          data: datapreset,
        })
          .then(() => {
            vm.updateCache();
          })
          .then(() => {
            $rootScope.$broadcast('REFRESH_LIST_VIEW', {});
          })
          .catch(function (data) {
            Notifications.add(
              $translate.instant('CONVERSION_VIEW.ERROR_RUN_ACTIONS') +
                ' ' +
                data.statusText +
                '(' +
                data.status +
                ')',
              'error'
            );
            $log.error('Problem running actions. Error from server: ' + angular.toJson(data));
          });
      } else if (datanewactions) {
        $http({
          method: 'POST',
          url: appConfig.djangoUrl + baseUrl + '/' + id + '/actiontool/',
          data: datanewactions,
        })
          .then(() => {
            vm.updateCache();
          })
          .then(() => {
            $rootScope.$broadcast('REFRESH_LIST_VIEW', {});
          })
          .catch(function (data) {
            Notifications.add(
              $translate.instant('CONVERSION_VIEW.ERROR_RUN_ACTIONS') +
                ' ' +
                data.statusText +
                '(' +
                data.status +
                ')',
              'error'
            );
            $log.error('Problem running actions. Error from server: ' + angular.toJson(data));
          });
      }
    };
  }
}
