export default class ImportCtrl {
  constructor($q, $rootScope, $scope, $http, IP, Profile, SA, Notifications, $uibModal, $translate) {
    var vm = this;
    $scope.angular = angular;
    vm.loadingSas = false;
    vm.importingSa = false;
    vm.saProfile = {
      profiles: [],
      profile: null,
    };

    vm.user = {
      username: null,
      password: null,
    };

    vm.url = null;

    vm.getSaProfiles = function() {
      $scope.error = null;
      var auth = window.btoa(vm.user.username + ':' + vm.user.password);
      var headers = {Authorization: 'Basic ' + auth};
      vm.loadingSas = true;

      vm.url = vm.url.replace(/\/+$/, '');
      $http({
        method: 'GET',
        url: vm.url + '/api/submission-agreements/',
        headers: headers,
        params: {
          published: true,
          pager: 'none',
        },
        noAuth: true,
      })
        .then(function(response) {
          vm.loadingSas = false;
          vm.saProfile.profiles = response.data;
          vm.select = true;
        })
        .catch(function(response) {
          vm.loadingSas = false;
          if (response.data && response.data.detail) {
            $scope.error = response.data.detail;
          }
        });
    };

    vm.importSa = function(sa) {
      var auth = window.btoa(vm.user.username + ':' + vm.user.password);
      var headers = {Authorization: 'Basic ' + auth};
      var promises = [];
      vm.importingSa = true;
      var pattern = vm.types ? new RegExp('^profile_(' + vm.types.join('|') + ')$') : new RegExp('^profile_');
      for (var key in sa) {
        if (pattern.test(key) && sa[key] != null) {
          promises.push(
            $http.get(vm.url + '/api/profiles/' + sa[key] + '/', {headers: headers}).then(function(response) {
              var data = response.data;
              return Profile.new(data)
                .$promise.then(function(response) {
                  return response;
                })
                .catch(function(response) {
                  vm.importingSa = false;
                  if (response.status == 409) {
                    profileExistsModal(data);
                  }
                  return response;
                });
            })
          );
        } else {
        }
      }
      $q.all(promises).then(function() {
        if (vm.types && !angular.isUndefined(vm.types)) {
          var pattern = new RegExp('^profile_(?!(' + vm.types.join('|') + ')$)');
          for (var key in sa) {
            if (pattern.test(key)) {
              delete sa[key];
            }
          }
        }
        SA.new(sa)
          .$promise.then(function(resource) {
            Notifications.add($translate.instant('IMPORT.SA_IMPORTED', resource), 'success', 5000, {isHtml: true});
            vm.select = false;
            vm.importingSa = false;
          })
          .catch(function(response) {
            vm.importingSa = false;
            if (response.status == 409) {
              saProfileExistsModal(sa);
            }
          });
      });
    };

    vm.addSaFromFile = function(sa) {
      if (angular.isUndefined(sa)) {
        sa = vm.saFromFile;
      }
      var parsedSa;
      try {
        parsedSa = JSON.parse(sa);
      } catch (e) {
        Notifications.add(e, 'error');
        return;
      }
      SA.new(parsedSa)
        .$promise.then(function(resource) {
          Notifications.add($translate.instant('IMPORT.SA_IMPORTED', resource), 'success', 5000, {isHtml: true});
          vm.select = false;
        })
        .catch(function(response) {
          if (response.status == 409) {
            saProfileExistsModal(parsedSa);
          }
        });
    };
    vm.addProfileFromFile = function(profile) {
      var parsedProfile;
      try {
        parsedProfile = JSON.parse(profile);
      } catch (e) {
        Notifications.add(e, 'error');
        return;
      }
      Profile.new(parsedProfile)
        .$promise.then(function(resource) {
          Notifications.add($translate.instant('IMPORT.PROFILE_IMPORTED', resource), 'success', 5000, {isHtml: true});
          return resource;
        })
        .catch(function(response) {
          if (response.status == 409) {
            profileExistsModal(parsedProfile);
          }
          return response;
        });
    };

    $scope.$watch(
      function() {
        return vm.saFromFile;
      },
      function() {
        if (vm.saFromFile) {
          vm.addSaFromFile(vm.saFromFile);
        }
      }
    );

    $scope.$watch(
      function() {
        return vm.profileFromFile;
      },
      function() {
        if (vm.profileFromFile) {
          vm.addProfileFromFile(vm.profileFromFile);
        }
      }
    );

    function saProfileExistsModal(profile) {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/modals/sa-exists-modal.html',
        controller: 'OverwriteModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: function() {
            return {
              profile: profile,
            };
          },
        },
      });
      modalInstance.result.then(function(data) {});
    }
    function profileExistsModal(profile) {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/modals/profile-exists-modal.html',
        controller: 'OverwriteModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: function() {
            return {
              profile: profile,
            };
          },
        },
      });
      modalInstance.result.then(function(data) {});
    }
    vm.triggerProfileUpload = function() {
      document.getElementById('profile-upload').click();
    };
    vm.triggerSaUpload = function() {
      document.getElementById('sa-upload').click();
    };
  }
}
