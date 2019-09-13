/*
    ESSArch is an open source archiving and digital preservation system

    ESSArch Tools for Producer (ETP)
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
*/

export default class PrepareSipCtrl {
  constructor(
    Profile,
    $log,
    $uibModal,
    $scope,
    $rootScope,
    $http,
    appConfig,
    listViewService,
    $anchorScroll,
    $controller,
    $timeout,
    $state,
    ContentTabs
  ) {
    const vm = this;
    const ipSortString = ['Created', 'Submitting', 'Submitted'];
    $controller('BaseCtrl', {$scope: $scope, vm: vm, ipSortString: ipSortString, params: {}});

    //Click function for ip table
    vm.selectSingleRow = function(row, options) {
      $scope.ips = [];
      if ($scope.ip !== null && $scope.ip.id == row.id) {
        $scope.ip = null;
        $rootScope.ip = null;
        if (angular.isUndefined(options) || !options.noStateChange) {
          $state.go($state.current.name, {id: null});
        }
      } else {
        $scope.ip = null;
        $rootScope.ip = null;
        vm.activeTab = null;
        $timeout(() => {
          $scope.ip = row;
          $rootScope.ip = row;
          if (angular.isUndefined(options) || !options.noStateChange) {
            $state.go($state.current.name, {id: $scope.ip.id});
          }
          const ip = row;
          if (vm.specificTabs.includes('submit_sip') || ContentTabs.visible([$scope.ip], $state.current.name)) {
            $http
              .get(appConfig.djangoUrl + 'information-packages/' + ip.id + '/profiles/', {
                params: {profile__profile_type: 'submit_description'},
              })
              .then(function(response) {
                const sd_profile_ip = response.data[0];
                vm.informationModel = sd_profile_ip.data.data;
                vm.informationFields = sd_profile_ip.profile.template;
                vm.informationFields.forEach(function(field) {
                  field.type = 'input';
                  field.templateOptions.disabled = true;
                });
                $http
                  .get(appConfig.djangoUrl + 'information-packages/' + ip.id + '/profiles/', {
                    params: {profile__profile_type: 'transfer_project'},
                  })
                  .then(function(response) {
                    const tp_profile_ip = response.data[0];
                    vm.dependencyModel = tp_profile_ip.data.data;
                    vm.dependencyFields = tp_profile_ip.profile.template;
                    vm.dependencyFields.forEach(function(field) {
                      field.type = 'input';
                      field.templateOptions.disabled = true;
                    });
                    listViewService.getFileList(ip).then(function(result) {
                      $scope.fileListCollection = result;
                      $scope.getPackageProfiles(row);
                      $scope.edit = true;
                      $scope.eventlog = true;
                    });
                  });
              })
              .catch(function(response) {
                console.log(response.status);
              });
          }
        });
      }
    };

    // Populate file list view
    vm.options = {
      formState: {},
    };
    //Get list of files in ip
    $scope.getFileList = function(ip) {
      listViewService.getFileList(ip).then(function(result) {
        $scope.fileListCollection = result;
      });
    };
    //Get package dependencies for ip(transfer_project profile)
    $scope.getPackageDependencies = function(ip) {
      if (ip.profile_transfer_project) {
        Profile.get({
          id: ip.profile_transfer_project.profile,
          ip: ip.id,
        }).$promise.then(function(resource) {
          vm.dependencyModel = resource.specification_data;
          vm.dependencyFields = resource.template;
          vm.dependencyFields.forEach(function(field) {
            field.templateOptions.disabled = true;
          });
        });
      }
    };
    vm.profileFields = [];
    vm.profileModel = {};
    //Get lock-status from profiles
    $scope.getPackageProfiles = function(ip) {
      vm.profileFields = [];
      vm.profileModel = {};
      if (ip.profile_transfer_project) {
        vm.profileModel.transfer_project = ip.profile_transfer_project.LockedBy != null;
        var field = {
          templateOptions: {
            label: 'transfer_project',
            disabled: true,
          },
          type: 'checkbox',
          key: 'transfer_project',
        };
        vm.profileFields.push(field);
      }
      if (ip.profile_submit_description) {
        vm.profileModel.submit_description = ip.profile_submit_description.LockedBy != null;
        var field = {
          templateOptions: {
            label: 'submit_description',
            disabled: true,
          },
          type: 'checkbox',
          key: 'submit_description',
        };
        vm.profileFields.push(field);
      }
      if (ip.profile_sip) {
        vm.profileModel.sip = ip.profile_sip.LockedBy != null;
        var field = {
          templateOptions: {
            label: 'sip',
            disabled: true,
          },
          type: 'checkbox',
          key: 'sip',
        };
        vm.profileFields.push(field);
      }
      if (ip.profile_aip) {
        vm.profileModel.aip = ip.profile_aip.LockedBy != null;
        var field = {
          templateOptions: {
            label: 'aip',
            disabled: true,
          },
          type: 'checkbox',
          key: 'aip',
        };
        vm.profileFields.push(field);
      }
      if (ip.profile_dip) {
        vm.profileModel.dip = ip.profile_dip.LockedBy != null;
        var field = {
          templateOptions: {
            label: 'dip',
            disabled: true,
          },
          type: 'checkbox',
          key: 'dip',
        };
        vm.profileFields.push(field);
      }
      if (ip.profile_content_type) {
        vm.profileModel.content_type = ip.profile_content_type.LockedBy != null;
        var field = {
          templateOptions: {
            label: 'content_type',
            disabled: true,
          },
          type: 'checkbox',
          key: 'content_type',
        };
        vm.profileFields.push(field);
      }

      if (ip.profile_authority_information) {
        vm.profileModel.authority_information = ip.profile_authority_information.LockedBy != null;
        var field = {
          templateOptions: {
            label: 'authority_information',
            disabled: true,
          },
          type: 'checkbox',
          key: 'authority_information',
        };
        vm.profileFields.push(field);
      }
      if (ip.profile_archival_description) {
        vm.profileModel.archival_description = ip.profile_archival_description.LockedBy != null;
        var field = {
          templateOptions: {
            label: 'archival_description',
            disabled: true,
          },
          type: 'checkbox',
          key: 'archival_description',
        };
        vm.profileFields.push(field);
      }
      if (ip.profile_preservation_metadata) {
        vm.profileModel.preservation_metadata = ip.profile_preservation_metadata.LockedBy != null;
        var field = {
          templateOptions: {
            label: 'preservation_metadata',
            disabled: true,
          },
          type: 'checkbox',
          key: 'preservation_metadata',
        };
        vm.profileFields.push(field);
      }
      if (ip.profile_event) {
        vm.profileModel.event = ip.profile_event.LockedBy != null;
        var field = {
          templateOptions: {
            label: 'event',
            disabled: true,
          },
          type: 'checkbox',
          key: 'event',
        };
        vm.profileFields.push(field);
      }
      if (ip.profile_data_selection) {
        vm.profileModel.data_selection = ip.profile_data_selection.LockedBy != null;
        var field = {
          templateOptions: {
            label: 'data_selection',
            disabled: true,
          },
          type: 'checkbox',
          key: 'data_selection',
        };
        vm.profileFields.push(field);
      }
      if (ip.profile_import) {
        vm.profileModel.import = ip.profile_import.LockedBy != null;
        var field = {
          templateOptions: {
            label: 'import',
            disabled: true,
          },
          type: 'checkbox',
          key: 'import',
        };
        vm.profileFields.push(field);
      }
      if (ip.profile_workflow) {
        vm.profileModel.workflow = ip.profile_workflow.LockedBy != null;
        var field = {
          templateOptions: {
            label: 'workflow',
            disabled: true,
          },
          type: 'checkbox',
          key: 'workflow',
        };
        vm.profileFields.push(field);
      }
    };
    //Get package information(submit-description)
    $scope.getPackageInformation = function(ip) {
      if (ip.profile_submit_description) {
        Profile.get({
          id: ip.profile_submit_description.profile,
          ip: ip.id,
        }).$promise.then(
          function(resource) {
            vm.informationModel = resource.specification_data;
            vm.informationFields = resource.template;
            vm.informationFields.forEach(function(field) {
              field.templateOptions.disabled = true;
            });
          },
          function(response) {
            console.log(response.status);
          }
        );
      }
    };
    //Get active profile
    function getActiveProfile(profiles) {
      return profiles.active;
    }

    $scope.emailModal = function(profiles) {
      if (vm.dependencyModel.preservation_organization_receiver_email) {
        const modalInstance = $uibModal.open({
          animation: true,
          ariaLabelledBy: 'modal-title',
          ariaDescribedBy: 'modal-body',
          templateUrl: 'static/frontend/views/email_modal.html',
          scope: $scope,
          size: 'lg',
          controller: 'DataModalInstanceCtrl',
          controllerAs: '$ctrl',
          resolve: {
            data: {
              ip: $scope.ip,
              vm: vm,
            },
          },
        });
        modalInstance.result
          .then(function(data) {
            $scope.eventlog = false;
            $scope.edit = false;
            $scope.getListViewData();
            vm.updateListViewConditional();
            $anchorScroll();
          })
          .catch(function() {
            $log.info('modal-component dismissed at: ' + new Date());
          });
      } else {
        vm.submitSipModal($scope.ip);
      }
    };
    vm.submitSipModal = function(ip) {
      const ips = $scope.ips.length > 0 ? $scope.ips : null;
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/submit_sip_modal.html',
        scope: $scope,
        controller: 'DataModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            ip: ip,
            ips: ips,
            vm: vm,
          },
        },
      });
      modalInstance.result
        .then(function(data) {
          $scope.ips = [];
          $scope.ip = null;
          $rootScope.ip = null;
          $scope.getListViewData();
          vm.updateListViewConditional();
          $anchorScroll();
        })
        .catch(function() {
          $log.info('modal-component dismissed at: ' + new Date());
        });
    };
  }
}
