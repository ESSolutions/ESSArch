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
    vm.collectedActions = [];
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
        if (vm.cache.get('selectedProfile')) {
          $scope.selectedProfile = vm.cache.get('selectedProfile');
        }
        if (vm.cache.get('nameOfWorkflow')) {
          vm.nameOfWorkflow = vm.cache.get('nameOfWorkflow');
        }
        if (vm.cache.get('collectedActions')) {
          vm.collectedActions = vm.cache.get('collectedActions');
        }
        vm.mergeArrays();

        vm.resetNewAndCollectedObjects();
      }

      if (vm.addedActions.length > 0) {
        vm.workflowActive = true;
      } else {
        vm.workflowActive = false;
      }
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
      vm.mergeArrays();
      vm.resetNewAndCollectedObjects();
      if (vm.profilespec.length < 1 && vm.addedActions.length < 1) {
        vm.profilespec = [];
        vm.addedActions = [];
        vm.mergeArrays();
        vm.updateCache();
        vm.resetNewAndCollectedObjects();
        vm.workflowActive = false;
      }
    };

    vm.mergeArrays = () => {
      vm.collectedActions = [];
      vm.collectedActions = vm.profilespec.concat(vm.addedActions);
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

      vm.put('collectedActions', vm.collectedActions);

      vm.put('ip.id', vm.ip.id);
    };

    vm.deleteAddedFromWorkflow = (value) => {
      if (vm.addedActions.length > 0) {
        var index = vm.addedActions.indexOf(value);
        vm.addedActions.splice(index, 1);
        vm.mergeArrays();

        if (vm.profilespec.length < 1 && vm.addedActions.length < 1) {
          vm.profilespec = [];
          vm.addedActions = [];
          vm.mergeArrays();
          vm.updateCache();
          vm.resetNewAndCollectedObjects();
          vm.workflowActive = false;
        }
      }
      vm.updateCache();
      vm.resetNewAndCollectedObjects();
    };

    vm.actionDetailsModal = (value, conversions) => {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/action_details_modal.html',
        scope: $scope,
        controller: [
          '$scope',
          '$uibModalInstance',
          '$translate',
          'data',
          function ($scope, $uibModalInstance, $translate, data) {
            $scope.fields = [];
            $scope.data = data.value;
            $scope.keep = [];

            if ($scope.data.args !== undefined) {
              for (let i = 0; i < vm.options.converters.length; i++) {
                var string1 = $scope.data.label;
                var string2 = vm.options.converters[i].name;
                var result = string1.localeCompare(string2);
                if (result === 0) {
                  $scope.receiverdata = data.value.args[2];
                  $scope.fields = vm.options.converters[i].form;
                }
              }
            }

            if ($scope.data.name) {
              for (var i = 0; i < vm.options.converters.length; i++) {
                var string1 = $scope.data.name;
                var string2 = vm.options.converters[i].name;
                var result = string1.localeCompare(string2);
                if (result === 0) {
                  $scope.fields = vm.options.converters[i].form;
                }
              }
            }

            $scope.cancel = function () {
              $uibModalInstance.dismiss('cancel');
              return;
            };

            $scope.save = function () {
              vm.saveWorkflowModal();
              $uibModalInstance.dismiss('cancel');
              return;
            };
          },
        ],
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
      if (vm.objectsFromAPI.length > 0 || (vm.addedActions.length > 0 && vm.workflowActive)) {
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

            if (vm.objectsFromAPI.length > 0) {
              vm.flowOptions = {};
              datapreset = angular.extend(vm.flowOptions, {
                actions: vm.objectsFromAPI.map((x) => {
                  if (x.args[1]) {
                    return {
                      name: x.args[0],
                      options: x.args[2],
                      path: x.args[1],
                    };
                  } else {
                    return {
                      name: x.args[0],
                      options: x.args[2],
                    };
                  }
                }),
                action_workflow_name: result.action_workflow_name,
                action_workflow_status: result.action_workflow_status,
              });
            }

            if (vm.addedActions.length > 0) {
              vm.flowOptions = {};
              datanewactions = angular.extend(vm.flowOptions, {
                actions: vm.addedActions.map((x) => {
                  if (x.path) {
                    return {
                      name: x.name,
                      options: x.options,
                      path: x.path,
                    };
                  } else {
                    return {
                      name: x.name,
                      options: x.options,
                    };
                  }
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
              .post(appConfig.djangoUrl + vm.baseUrl + '/' + vm.ip.id + '/actiontool_save_as/', data)
              .then((response) => {
                $rootScope.$broadcast('REFRESH_LIST_VIEW', {});
                Notifications.add('Saved workflow ' + result.action_workflow_name, 'success');
                vm.getProfiles();
              })
              .then(() => {
                //vm.cancelWorkflow();
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
    };

    vm.cancelWorkflow = () => {
      vm.profilespec = [];
      vm.addedActions = [];
      vm.collectedActions = [];
      vm.mergeArrays();
      vm.nameOfWorkflow = '';
      $scope.selectedProfile = null;
      vm.updateCache();
      vm.resetNewAndCollectedObjects();
    };

    vm.saveWorkflowModal = () => {
      if (vm.objectsFromAPI.length > 0 || (vm.addedActions.length > 0 && vm.workflowActive)) {
        var workflow = $scope.selectedProfile;
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

            if (vm.objectsFromAPI.length > 0) {
              vm.flowOptions = {};
              datapreset = angular.extend(vm.flowOptions, {
                actions: vm.objectsFromAPI.map((x) => {
                  if (x.args[1]) {
                    return {
                      name: x.args[0],
                      options: x.args[2],
                      path: x.args[1],
                    };
                  } else {
                    return {
                      name: x.args[0],
                      options: x.args[2],
                    };
                  }
                }),
                action_workflow_name: result.action_workflow_name,
                action_workflow_status: result.action_workflow_status,
              });
            }

            if (vm.newObjects.length > 0) {
              vm.flowOptions = {};
              datanewactions = angular.extend(vm.flowOptions, {
                actions: vm.newObjects.map((x) => {
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

            if (vm.objectsFromAPI.length > 0 && vm.newObjects.length > 0) {
              datapreset.actions = datapreset.actions.concat(datanewactions.actions);
              data = datapreset;
            } else if (vm.newObjects.length > 0) {
              data = datanewactions;
            } else if (vm.objectsFromAPI.length > 0) {
              data = datapreset;
            }

            $http
              .post(appConfig.djangoUrl + vm.baseUrl + '/' + vm.ip.id + '/actiontool_save_as/', data)
              .then((response) => {
                $rootScope.$broadcast('REFRESH_LIST_VIEW', {});
                Notifications.add('Saved workflow ' + result.action_workflow_name, 'success');
                vm.nameOfWorkflow = result.action_workflow_name;
                $scope.selectedProfile = {
                  name: result.action_workflow_name,
                  status: result.action_workflow_status,
                };
                vm.updateCache();
                vm.getProfiles();
                vm.resetNewAndCollectedObjects();
              })
              .then(() => {
                //vm.cancelWorkflow();
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
      if (!angular.isUndefined($scope.selectedProfile) && $scope.selectedProfile !== null) {
        if (
          !angular.isUndefined($scope.selectedProfile.id) &&
          $scope.selectedProfile.id !== null &&
          $scope.selectedProfile.id !== ''
        ) {
          $http({
            url: appConfig.djangoUrl + 'profiles/' + $scope.selectedProfile.id + '/',
            method: 'GET',
            params: {pager: 'none'},
          })
            .then(function (response) {
              vm.addedActions = [];
              vm.profilespec = response.data.specification[0].children;
              vm.mergeArrays();
            })
            .then(function () {
              vm.nameOfWorkflow = $scope.selectedProfile.name;
              vm.updateCache();
              vm.resetNewAndCollectedObjects();
            })
            .catch(function (data) {
              Notifications.add(
                $translate.instant('CONVERSION_VIEW.ERROR_GET_PROFILES') +
                  ' ' +
                  data.statusText +
                  '(' +
                  data.status +
                  ')',
                'error'
              );
              $log.error('Error getting profiles from server: ' + angular.toJson(data));
            });

          vm.workflowActive = true;
        }
      }
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
                actions: vm.conversions.map((conversions_item) => {
                  action_name = angular.copy(conversions_item.converter.name);
                  action_options = angular.copy(conversions_item.data);
                  action_path = angular.copy(conversions_item.data.path);
                  return {
                    name: action_name,
                    options: action_options,
                    path: action_path,
                  };
                }),
              });
            } catch (e) {
              Notifications.add($translate.instant('CONVERSION_VIEW.ERROR_ADDING_TO_LIST') + ' ' + e, 'error');
              $log.error('Error adding action to list: ' + angular.toJson(e));
            }
          }
        }
      }
      addAction = {};

      addAction.name = action_name;
      addAction.options = action_options;
      addAction.path = action_path;
      addAction.data = data;

      vm.addedActions.push(addAction);
      vm.conversions[0].data = {};
      vm.fields = [];
      vm.mergeArrays();

      vm.updateCache();

      vm.resetNewAndCollectedObjects();

      vm.workflowActive = true;
    };

    vm.resetNewAndCollectedObjects = () => {
      vm.newObjects = [];
      vm.objectsFromAPI = [];
      for (var i = 0; i < vm.collectedActions.length; i++) {
        if (vm.collectedActions[i].args !== undefined) {
          vm.objectsFromAPI.push(vm.collectedActions[i]);
        }
        if (vm.collectedActions[i].args == undefined) {
          vm.newObjects.push(vm.collectedActions[i]);
        }
      }
    };

    vm.startPresetConversion = () => {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/are_you_sure_modal.html',
        scope: $scope,
        controller: [
          '$scope',
          '$uibModalInstance',
          '$translate',
          function ($scope, $uibModalInstance) {
            $scope.run = true;
            $scope.cancel = function () {
              $uibModalInstance.dismiss('cancel');
              $scope.run = false;
              return false;
            };

            $scope.yes = function () {
              $uibModalInstance.dismiss('cancel');
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
              vm.resetNewAndCollectedObjects();

              if (vm.objectsFromAPI.length > 0) {
                vm.flowOptions = {};
                datapreset = angular.extend(vm.flowOptions, {
                  actions: vm.objectsFromAPI.map((x) => {
                    if (x.args[1]) {
                      return {
                        name: x.args[0],
                        options: x.args[2],
                        path: x.args[1],
                      };
                    }
                    return {
                      name: x.args[0],
                      options: x.args[2],
                    };
                  }),
                });
              }

              if (vm.newObjects.length > 0) {
                vm.flowOptions = {};
                datanewactions = angular.extend(vm.flowOptions, {
                  actions: vm.newObjects.map((x) => {
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
                    vm.resetNewAndCollectedObjects();
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
                    vm.resetNewAndCollectedObjects();
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
                    vm.resetNewAndCollectedObjects();
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
              return true;
            };
          },
        ],
      });
      modalInstance.result.then(
        () => {
          $scope.run = false;
        },
        function () {}
      );
    };
  }
}
