export default class SaEditorCtrl {
  constructor(Notifications, $timeout, SA, Profile, $scope, $rootScope, $http, appConfig, $anchorScroll, $translate) {
    const vm = this;
    $scope.edit = false;
    vm.saProfile = null;
    vm.saProfiles = [];
    vm.createNewSa = false;
    vm.saLoading = false;
    vm.$onInit = function() {
      SA.query({pager: 'none'}).$promise.then(function(resource) {
        vm.saProfiles = resource;
      });
    };
    vm.newSa = function(use_template) {
      vm.saLoading = true;
      vm.getProfiles().then(function() {
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
      });
    };

    vm.chooseSa = function(sa) {
      vm.saLoading = true;
      vm.getProfiles()
        .then(function(resource) {
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
        })
        .catch(function(response) {
          vm.saProfile = null;
          vm.saModel = null;
          $scope.edit = false;
          vm.saLoading = false;
        });
    };

    vm.disableFields = function() {
      vm.saFields.forEach(function(field) {
        field.templateOptions.disabled = true;
      });
    };

    vm.enableFields = function() {
      vm.saFields.forEach(function(field) {
        field.templateOptions.disabled = false;
      });
    };
    vm.createProfileModel = function(sa) {
      for (const key in sa) {
        if (/^profile/.test(key) && sa[key] != null) {
          vm.profileModel[key] = sa[key];
        }
      }
    };
    vm.getProfiles = function() {
      return Profile.query().$promise.then(function(resource) {
        resource.forEach(function(profile) {
          if (vm.profiles[profile.profile_type]) {
            vm.profiles[profile.profile_type].forEach(function(item, idx, array) {
              if (item.id == profile.id) {
                array.splice(idx, 1);
              }
            });
            vm.profiles[profile.profile_type].push(profile);
          }
        });
        return resource;
      });
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
          vm.getProfiles();
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

    // Fill the profile fields with available profile options
    $http.get(appConfig.djangoUrl + 'submission-agreement-template/').then(function(response) {
      vm.saFields = response.data.map(function(field) {
        if (field.key.startsWith('profile_')) {
          const profile_type = field.key.replace('profile_', '');
          field.templateOptions.options = vm.profiles[profile_type];
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
  }
}
