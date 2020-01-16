export default class SaEditorCtrl {
  constructor(Notifications, $timeout, SA, Profile, $scope, $rootScope, $http, appConfig, $anchorScroll, $translate) {
    const vm = this;
    $scope.edit = false;
    vm.saProfile = null;
    vm.saProfiles = [];
    vm.createNewSa = false;
    vm.saLoading = false;
    vm.profileOptions = {};
    vm.policyOptions = [];
    vm.$onInit = function() {
      SA.query({pager: 'none'}).$promise.then(function(resource) {
        vm.saProfiles = resource;
      });

      // Fill the profile fields with available profile options
      $http.get(appConfig.djangoUrl + 'submission-agreement-template/').then(function(response) {
        vm.saFields = response.data.map(function(field) {
          if (field.key.startsWith('profile_') && !field.templateOptions.useTemplate) {
            field = getProfileSelectField(angular.copy(field));
          }
          if (field.key === 'policy' && !field.templateOptions.useTemplate) {
            field = policyField;
          }
          return field;
        });
        for (let i = 0; i < vm.saFields.length; i++) {
          if (!vm.saFields[i].templateOptions.disabled) {
            vm.saFields[i].templateOptions.focus = true;
            break;
          }
        }
      });
    };

    let policyField = {
      type: 'uiselect',
      key: 'policy',
      templateOptions: {
        options: function() {
          return vm.policyOptions;
        },
        valueProp: 'id',
        labelProp: 'policy_id',
        label: $translate.instant('STORAGE_POLICY'),
        appendToBody: true,
        refresh: (search, open, value) => {
          if (open || (!open && value)) {
            if (angular.isUndefined(search) || search === null || search === '') {
              search = '';
            }
            return vm.getPolicy(search).then(() => {
              this.options = vm.policyOptions;
              return vm.policyOptions;
            });
          }
        },
      },
    };

    vm.getPolicy = search => {
      return $http({
        url: appConfig.djangoUrl + 'storage-policies/',
        mathod: 'GET',
        params: {pager: 'none', search: search},
      }).then(function(response) {
        vm.policyOptions = response.data;
        return vm.policyOptions;
      });
    };

    let getProfileSelectField = field => {
      const type = field.key.replace('profile_', '');
      if (angular.isUndefined(vm.profileOptions[type])) {
        vm.profileOptions[type] = [];
      }
      return {
        type: 'uiselect',
        key: field.key,
        templateOptions: {
          options: function() {
            return vm.profileOptions[type];
          },
          valueProp: 'id',
          labelProp: 'name',
          placeholder: field.templateOptions.placeholder ? field.templateOptions.placeholder : '',
          label: field.templateOptions.label,
          clearEnabled: true,
          required: field.templateOptions.required ? field.templateOptions.required : false,
          appendToBody: true,
          refresh: (search, open, value) => {
            if (open || (!open && value)) {
              if (angular.isUndefined(search) || search === null || search === '') {
                search = '';
              }
              return vm.getProfilesByType(type, search).then(() => {
                this.options = vm.profileOptions[type];
                return vm.profileOptions[type];
              });
            }
          },
        },
      };
    };

    vm.getProfilesByType = (type, search) => {
      return $http({
        url: appConfig.djangoUrl + 'profiles/',
        mathod: 'GET',
        params: {pager: 'none', search: search, type},
      }).then(function(response) {
        vm.profileOptions[type] = response.data;
        return vm.profileOptions[type];
      });
    };

    vm.newSa = function(use_template) {
      vm.saLoading = true;
      vm.enableFields();
      vm.saModel = null;
      if (use_template && !angular.isUndefined(use_template)) {
        const sa = angular.copy(vm.saProfile);
        vm.saProfile = null;
        delete sa.id;
        delete sa.url;
        sa.published = false;
        sa.name = '';
        $timeout(function() {
          vm.saModel = sa;
          vm.saProfiles.push(vm.saModel);
          vm.saProfile = vm.saModel;
          vm.saLoading = false;
        });
      } else {
        vm.saProfile = null;
        $timeout(function() {
          vm.saModel = {};
          vm.saProfiles.push(vm.saModel);
          vm.saProfile = vm.saModel;
          vm.saLoading = false;
        });
      }
      vm.createNewSa = true;
      $scope.edit = true;
    };

    vm.chooseSa = function(sa) {
      vm.saLoading = true;
      vm.saProfile = sa;
      vm.saModel = null;
      if (sa.published) {
        vm.disableFields();
      } else {
        vm.enableFields();
      }
      $timeout(function() {
        vm.saModel = sa;
      });
      vm.createNewSa = false;
      $scope.edit = true;
      vm.saLoading = false;
    };

    vm.disableFields = function() {
      vm.saFields.forEach(function(field) {
        field.templateOptions.disabled = true;
        if (field.templateOptions.clearEnabled) {
          field.templateOptions.clearEnabled = false;
        }
      });
    };

    vm.enableFields = function() {
      vm.saFields.forEach(function(field) {
        field.templateOptions.disabled = false;
        if (field.templateOptions.clearEnabled === false) {
          field.templateOptions.clearEnabled = true;
        }
      });
    };
    vm.createProfileModel = function(sa) {
      for (const key in sa) {
        if (/^profile/.test(key) && sa[key] != null) {
          vm.profileModel[key] = sa[key];
        }
      }
    };

    vm.saveSa = function() {
      if (vm.createNewSa) {
        vm.saveNewSa();
      } else {
        vm.updateSa();
      }
    };

    vm.saveNewSa = function() {
      const newSa = new SA(vm.saModel);
      newSa.$save().then(function(savedSa) {
        vm.createNewSa = false;
        vm.saProfile = null;
        vm.saModel = {};
        $scope.edit = false;
        SA.query({pager: 'none'}).$promise.then(function(resource) {
          vm.saProfiles = resource;
          vm.saProfiles.forEach(function(sa) {
            if (sa.id == savedSa.id) {
              vm.saProfile = sa;
            }
          });
          vm.chooseSa(vm.saProfile);
          $anchorScroll();
        });
        return savedSa;
      });
    };

    vm.updateSa = function() {
      SA.update(vm.saModel).$promise.then(function(savedSa) {
        vm.createNewSa = false;
        vm.saProfile = null;
        vm.saModel = {};
        $scope.edit = false;
        SA.query({pager: 'none'}).$promise.then(function(resource) {
          vm.saProfiles = resource;
          vm.saProfiles.forEach(function(sa) {
            if (sa.id == savedSa.id) {
              vm.saProfile = sa;
            }
          });
          vm.chooseSa(vm.saProfile);
          $anchorScroll();
        });
        return savedSa;
      });
    };

    vm.publishSa = function() {
      SA.publish({id: vm.saProfile.id}).$promise.then(function(resource) {
        SA.query({pager: 'none'}).$promise.then(function(resource) {
          vm.saProfiles = resource;
          vm.saProfiles.forEach(function(sa) {
            if (sa.id == vm.saProfile.id) {
              vm.saProfile = sa;
            }
          });
          vm.chooseSa(vm.saProfile);
          $scope.edit = false;
          Notifications.add($translate.instant('SA_PUBLISHED', vm.saProfile), 'success', 5000);
        });
        return resource;
      });
    };

    vm.profiles = {
      transfer_project: [],
      content_type: [],
      data_selection: [],
      authority_information: [],
      archival_description: [],
      import: [],
      submit_description: [],
      sip: [],
      aic_description: [],
      aip: [],
      aip_description: [],
      dip: [],
      workflow: [],
      preservation_metadata: [],
    };
    vm.saModel = {};
    vm.saFields = [];
  }
}
