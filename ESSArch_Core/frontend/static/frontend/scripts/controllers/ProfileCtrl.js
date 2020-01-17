import reduce from 'lodash/reduce';

export default class ProfileCtrl {
  constructor(
    SA,
    IP,
    Profile,
    PermPermissionStore,
    ProfileIp,
    ProfileIpData,
    $scope,
    listViewService,
    $log,
    $uibModal,
    $translate,
    $filter,
    $http,
    appConfig,
    SaIpData
  ) {
    const vm = this;
    $scope.angular = angular;
    $scope.select = true;
    $scope.alerts = {
      error: {type: 'danger', msg: $translate.instant('ERROR')},
      noSas: {type: 'danger', msg: $translate.instant('NO_SUBMISSION_AGREEMENT_AVAILABLE')},
    };
    $scope.saAlert = null;
    $scope.aipAlert = $scope.alerts.aipError;
    $scope.dipAlert = $scope.alerts.dipError;
    vm.dataVersion = null;
    $scope.saProfile = {
      profile: null,
      profiles: [],
      disabled: false,
    };
    $scope.selectRowCollapse = [];
    // On init
    vm.$onInit = function() {
      init();
    };

    vm.$onChanges = function(changes) {
      if (!changes.ip.isFirstChange()) {
        init();
      }
    };

    function init() {
      $scope.saProfile = {
        profile: null,
        profiles: [],
        disabled: false,
      };
      $scope.ip = vm.ip;
      if (!vm.types) {
        vm.types = {
          transfer_project: {visible: true, disabled: false},
          submit_description: {visible: true, disabled: false},
          sip: {visible: true, disabled: false},
          aic_description: {visible: true, disabled: false},
          aip: {visible: true, disabled: false},
          aip_description: {visible: true, disabled: false},
          dip: {visible: true, disabled: false},
          workflow: {visible: true, disabled: false},
          preservation_metadata: {visible: true, disabled: false},
        };
      }
      vm.cancel();
      vm.saCancel();
      vm.gettingSas = true;
      listViewService.getSaProfiles($scope.ip).then(function(result) {
        vm.gettingSas = false;
        $scope.saProfile.profiles = result.profiles;
        $scope.saProfile.locked = result.locked;
        let chosen_sa_id = null;
        if ($scope.ip.submission_agreement) {
          chosen_sa_id = $scope.ip.submission_agreement;
        } else if ($scope.ip.submission_agreement == null && result.profiles.length > 0) {
          chosen_sa_id = $scope.saProfile.profiles[0].id;
          $scope.changeSaProfile($scope.saProfile.profiles[0], $scope.ip);
        }
        if (result.profiles.length <= 0) {
          $scope.saAlert = $scope.alerts.noSas;
        } else if (chosen_sa_id) {
          const found = $filter('filter')(result.profiles, {id: chosen_sa_id}, true);
          if (found.length) {
            $scope.saProfile.profile = found[0];
          } else {
            $scope.saAlert = $scope.alerts.error;
          }
        }
        vm.loadProfiles();
      });
    }

    vm.loadProfiles = function() {
      const sa = $scope.saProfile.profile;
      $scope.profilesLoading = true;
      $scope.selectRowCollection = [];
      SA.profiles({id: sa.id}).$promise.then(function(resource) {
        $scope.profilesLoading = false;
        $scope.selectRowCollection = resource.filter(x => vm.types[x.profile_type]);
      });
    };

    vm.changeDataVersion = function(profileIp, data) {
      ProfileIp.patch({id: profileIp.id}, {data: data}).$promise.then(function(resource) {
        vm.getAndShowProfile(vm.selectedProfile, {});
      });
    };

    vm.getSas = search => {
      return $http
        .get(appConfig.djangoUrl + 'submission-agreements/', {params: {page: 1, page_size: 10, search}})
        .then(response => {
          $scope.saProfile.profiles = response.data;
          return response.data;
        });
    };

    vm.saProfileOptions = () => {
      return $scope.saProfile.profiles;
    };

    $scope.pushData = function() {
      vm.shareData({
        $event: {
          aipProfileId: $scope.saProfile.profile.profile_aip.id,
          dipProfileId: $scope.saProfile.profile.profile_dip.id,
          aipModel: vm.savedAip,
          dipModel: vm.savedDip,
          submissionAgreement: $scope.saProfile.profile.id,
        },
      });
    };
    $scope.$on('get_profile_data', function() {
      $scope.pushData();
    });

    vm.saveProfileModel = function(type, model) {
      vm.savingProfileModel = true;
      ProfileIpData.post({
        relation: vm.profileIp.id,
        version: vm.profileIp.data_versions.length,
        data: vm.profileModel,
      })
        .$promise.then(function(resource) {
          ProfileIp.patch({id: vm.profileIp.id}, {data: resource.id})
            .$promise.then(function(response) {
              vm.savingProfileModel = false;
              vm.cancel();
              return response;
            })
            .catch(function(response) {
              vm.savingProfileModel = false;
            });
        })
        .catch(function(response) {
          vm.savingProfileModel = false;
        });
    };

    vm.cancel = function() {
      vm.profileModel = {};
      vm.profileFields = [];
      $scope.profileToSave = null;
      vm.selectedProfile = null;
    };
    vm.saCancel = function() {
      vm.saModel = {};
      vm.saFields = [];
      $scope.selectedSa = null;
      $scope.editSa = false;
    };

    vm.profileModel = {};
    vm.profileFields = [];
    vm.options = {};

    vm.saModel = {};
    vm.saFields = [];
    vm.saOldModel = {};

    //Click function for sa view
    $scope.saClick = function(row) {
      vm.loadingSa = true;
      if ($scope.selectedSa && $scope.selectedSa.id === row.id && $scope.editSA) {
        vm.loadingSa = false;
        vm.saCancel();
        $scope.editSA = false;
      } else {
        $scope.selectedSa = row;
        $scope.eventlog = false;
        $scope.edit = false;
        vm.getAndShowSa(row, {});
        vm.loadingSa = false;
        $scope.editSA = true;
      }
    };

    vm.saFieldsLoading = function() {
      let val = false;
      angular.forEach(vm.loadingSaData, function(value, key) {
        if (value === true) {
          val = true;
        }
      });
      return val;
    };

    vm.saIp = null;
    vm.selectedSa = null;
    vm.loadingSaData = {};
    vm.getAndShowSa = function(sa, row) {
      vm.loadingSaData = true;
      vm.selectedSa = sa;
      SA.get({
        id: sa.id,
      })
        .$promise.then(function(resource) {
          if ($scope.ip.submission_agreement_data && $scope.ip.submission_agreement_data.id) {
            const data = $scope.ip.submission_agreement_data.data;
            const versions = $scope.ip.submission_agreement_data_versions;
            vm.saOldModel = angular.copy(data);
            vm.saModel = angular.copy(data);
            vm.saDataVersion = $scope.ip.submission_agreement_data.id;
            vm.saDataVersionList = versions;
            vm.saFields = vm.getSaFields(sa);
            vm.loadingSaData = false;
          } else {
            if ($scope.ip.submission_agreement_data && $scope.ip.submission_agreement_data.data) {
              vm.saOldModel = angular.copy($scope.ip.submission_agreement_data.data);
              vm.saModel = angular.copy($scope.ip.submission_agreement_data.data);
            } else {
              vm.saOldModel = {};
              vm.saModel = {};
            }
            vm.saDataVersion = null;
            vm.saDataVersionList = [];
            vm.saFields = vm.getSaFields(sa);
            vm.loadingSaData = false;
          }
        })
        .catch(function(response) {
          vm.loadingSaData = false;
          vm.saCancel();
        });
    };

    vm.getSaData = function(ip, sa) {
      return SaIpData.get({ip: ip.id, sa: sa.id, pager: 'none'}).$promise.then(function(resource) {
        let current = null;
        resource.forEach(x => {
          if (x.id === ip.submission_agreement_data) {
            current = x;
          }
        });

        return {current, list: resource};
      });
    };

    vm.changeSaDataVersion = version => {
      return $http({
        url: appConfig.djangoUrl + 'information-packages/' + $scope.ip.id + '/',
        method: 'PATCH',
        data: {
          submission_agreement_data: version,
        },
      }).then(response => {
        $scope.ip = response.data;
        vm.getAndShowSa($scope.saProfile.profile, {});
        $scope.$emit('REFRESH_LIST_VIEW', {});
        return response.data;
      });
    };

    vm.getSaFields = sa => {
      const temp = [];
      sa.template.forEach(function(x) {
        if (!x.templateOptions.disabled) {
          if (vm.disabled || $scope.saProfile.locked) {
            x.templateOptions.disabled = true;
            x.type = 'input';
          }
        }
        if (!x.hidden) {
          temp.push(x);
        }
      });
      return temp;
    };

    vm.savingSaModel = false;
    vm.saveSaModel = function(sa, model) {
      vm.savingSaModel = true;
      return SaIpData.post({
        information_package: $scope.ip.id,
        submission_agreement: sa.id,
        data: model,
        version: $scope.ip.submission_agreement_data_versions.length,
      })
        .$promise.then(function(resource) {
          return $http({
            url: appConfig.djangoUrl + 'information-packages/' + $scope.ip.id + '/',
            method: 'PATCH',
            data: {
              submission_agreement_data: resource.id,
            },
          })
            .then(response => {
              vm.savingSaModel = false;
              $scope.ip = response.data;
              $scope.$emit('REFRESH_LIST_VIEW', {});
              vm.saCancel();
              return response.data;
            })
            .catch(response => {
              vm.savingSaModel = false;
              return response;
            });
        })
        .catch(function(response) {
          vm.savingSaModel = false;
        });
    };

    //Click function for profile view
    $scope.profileClick = function(row) {
      if (vm.selectedProfile && vm.selectedProfile.id == row.id) {
        $scope.eventlog = false;
        $scope.edit = false;
        vm.cancel();
      } else {
        $scope.editSA = false;
        vm.getAndShowProfile(row, {});
        $scope.edit = true;
      }
    };

    vm.fieldsLoading = function() {
      let val = false;
      angular.forEach(vm.loadingProfileData, function(value, key) {
        if (value === true) {
          val = true;
        }
      });
      return val;
    };

    vm.profileIp = null;
    vm.selectedProfile = null;
    vm.loadingProfileData = {};
    vm.getAndShowProfile = function(profile, row) {
      vm.loadingProfileData[profile.profile_type] = true;
      vm.selectedProfile = profile;
      $scope.selectedNode = null;
      Profile.get({
        id: profile.id,
      })
        .$promise.then(function(resource) {
          ProfileIp.query({profile: resource.id, ip: $scope.ip.id})
            .$promise.then(function(profileIp) {
              resource.profile_name = resource.name;
              row.active = resource;
              row.profiles = [resource];
              $scope.selectProfile = row;
              if (profileIp[0].data == null) {
                profileIp[0].data = {data: {}};
              }
              vm.profileOldModel = angular.copy(profileIp[0].data.data);
              vm.profileModel = angular.copy(profileIp[0].data.data);
              vm.profileIp = profileIp[0];
              vm.dataVersion = vm.profileIp.data_versions[vm.profileIp.data_versions.indexOf(vm.profileIp.data.id)];
              getStructure(row.active);
              const temp = [];
              row.active.template.forEach(function(x) {
                if (!x.templateOptions.disabled) {
                  if (
                    vm.disabled ||
                    (vm.types[row.active.profile_type] && vm.types[row.active.profile_type].disabled)
                  ) {
                    x.templateOptions.disabled = true;
                    x.type = 'input';
                  }
                }
                if (!x.hidden) {
                  temp.push(x);
                }
              });
              $scope.profileToSave = row.active;
              vm.profileFields = temp;
              $scope.edit = true;
              $scope.eventlog = true;
              vm.loadingProfileData[profile.profile_type] = false;
            })
            .catch(function(response) {
              vm.profileFields = [];
              $scope.edit = true;
              $scope.eventlog = true;
              vm.loadingProfileData[profile.profile_type] = false;
            });
        })
        .catch(function(response) {
          vm.loadingProfileData[profile.profile_type] = false;
          vm.cancel();
        });
    };

    vm.getProfileData = function(id) {
      ProfileIpData.get({id: id}).$promise.then(function(resource) {
        vm.profileModel = angular.copy(resource.data);
      });
    };

    //Changes SA profile for selected ip
    $scope.changeSaProfile = function(sa, ip, oldSa_idx) {
      vm.changingSa = true;
      IP.changeSa({id: ip.id}, {submission_agreement: sa.id})
        .$promise.then(function(resource) {
          $scope.ip = resource;
          $scope.saProfile.profile = sa;
          vm.loadProfiles();
          if (vm.saFields.length > 0) {
            vm.saCancel();
          }
          $scope.$emit('REFRESH_LIST_VIEW', {});
          vm.changingSa = false;
        })
        .catch(function(response) {
          vm.changingSa = false;
        });
    };

    function showRequiredProfileFields(row) {
      if ($scope.edit) {
        $scope.lockAlert = $scope.alerts.lockError;
        $scope.lockAlert.name = row.active.profile_name;
        $scope.lockAlert.profile_type = row.active.profile_type;
        vm.editForm.$setSubmitted();
        return;
      }
      if (row.active.name) {
        var profileId = row.active.id;
      } else {
        var profileId = row.active.profile;
      }
      Profile.get({
        id: profileId,
        sa: $scope.saProfile.profile.id,
        ip: $scope.ip.id,
      }).$promise.then(function(resource) {
        resource.profile_name = resource.name;
        row.active = resource;
        row.profiles = [resource];
        $scope.selectProfile = row;
        vm.profileModel = angular.copy(row.active.specification_data);
        vm.profileFields = row.active.template;
        $scope.treeElements = [{name: 'root', type: 'folder', children: angular.copy(row.active.structure)}];
        $scope.expandedNodes = [];
        $scope.profileToSave = row.active;
        $scope.subSelectProfile = 'profile';
        if (row.locked) {
          vm.profileFields.forEach(function(field) {
            if (field.fieldGroup != null) {
              field.fieldGroup.forEach(function(subGroup) {
                subGroup.fieldGroup.forEach(function(item) {
                  item.type = 'input';
                  item.templateOptions.disabled = true;
                });
              });
            } else {
              field.type = 'input';
              field.templateOptions.disabled = true;
            }
          });
        }
        $scope.edit = true;
        $scope.eventlog = true;
      });
    }

    $scope.checkPermission = function(permissionName) {
      return !angular.isUndefined(PermPermissionStore.getPermissionDefinition(permissionName));
    };

    //Creates modal for lock SA
    $scope.lockSaModal = function(sa) {
      $scope.saProfile = sa;
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/lock-sa-profile-modal.html',
        scope: $scope,
        size: 'lg',
        controller: 'ModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {data: () => {}},
      });
      modalInstance.result.then(
        function(data) {
          $scope.lockSa($scope.saProfile);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    //Lock a SA
    $scope.lockSa = function(sa) {
      SA.lock({
        id: sa.profile.id,
        ip: $scope.ip.id,
      }).$promise.then(function(response) {
        sa.locked = true;
        vm.saCancel();
        $scope.$emit('REFRESH_LIST_VIEW', {});
        $scope.$emit('RELOAD_IP', {});
      });
    };

    // Map for profile types
    const typeMap = {
      transfer_project: 'Transfer Project',
      content_type: 'Content Type',
      data_selection: 'Data Selection',
      authority_information: 'Authority Information',
      archival_description: 'Archival Description',
      import: 'Import',
      submit_description: 'Submit Description',
      sip: 'SIP',
      aip: 'AIP',
      aic_description: 'AIC Description',
      aip_description: 'AIP Description',
      dip: 'DIP',
      workflow: 'Workflow',
      preservation_metadata: 'Preservation Metadata',
      validation: 'Validation',
    };

    /**
     * Maps profile type to a prettier format
     * @param {String} type
     */
    vm.mapProfileType = function(type) {
      return typeMap[type] || type;
    };

    vm.treeEditModel = {};
    vm.treeEditFields = [
      {
        templateOptions: {
          type: 'text',
          label: $translate.instant('NAME'),
          required: true,
        },
        type: 'input',
        key: 'name',
      },
      {
        templateOptions: {
          type: 'text',
          label: $translate.instant('TYPE'),
          options: [
            {name: 'folder', value: 'folder'},
            {name: 'file', value: 'file'},
          ],
          required: true,
        },
        type: 'select',
        key: 'type',
      },
      {
        // File uses
        templateOptions: {
          type: 'text',
          label: $translate.instant('USE'),
          options: [
            {name: 'Premis file', value: 'preservation_description_file'},
            {name: 'Mets file', value: 'mets_file'},
            {name: 'Archival Description File', value: 'archival_description_file'},
            {name: 'Authoritive Information File', value: 'authoritive_information_file'},
            {name: 'XSD Files', value: 'xsd_files'},
          ],
        },
        hideExpression: function($viewValue, $modelValue, scope) {
          return scope.model.type != 'file';
        },
        expressionProperties: {
          'templateOptions.required': function($viewValue, $modelValue, scope) {
            return scope.model.type == 'file';
          },
        },
        type: 'select-tree-edit',
        key: 'use',
        defaultValue: 'Pick one',
      },
    ];

    $scope.treeOptions = {
      nodeChildren: 'children',
      dirSelectable: true,
      injectClasses: {
        ul: 'a1',
        li: 'a2',
        liSelected: 'a7',
        iExpanded: 'a3',
        iCollapsed: 'a4',
        iLeaf: 'a5',
        label: 'a6',
        labelSelected: 'a8',
      },
      isLeaf: function(node) {
        return node.type == 'file';
      },
      equality: function(node1, node2) {
        return node1 === node2;
      },
      isSelectable: function(node) {
        return !$scope.updateMode.active && !$scope.addMode.active;
      },
    };

    //Populate map structure tree view given tree width and amount of levels
    function getStructure(profile) {
      $scope.treeElements = [{name: 'root', type: 'folder', children: profile.structure}];
      $scope.expandedNodes = [];
    }
    $scope.treeElements = []; //[{name: "Root", type: "Folder", children: createSubTree(3, 4, "")}];
    $scope.currentNode = null;
    $scope.selectedNode = null;
    //Add node to map structure tree view
    $scope.addNode = function(node) {
      const dir = {
        name: vm.treeEditModel.name,
        type: vm.treeEditModel.type,
      };
      if (vm.treeEditModel.type == 'folder') {
        dir.children = [];
      }
      if (vm.treeEditModel.type == 'file') {
        dir.use = vm.treeEditModel.use;
      }
      if (node == null) {
        $scope.treeElements[0].children.push(dir);
      } else {
        node.node.children.push(dir);
      }
      $scope.exitAddMode();
    };
    //Remove node from map structure tree view
    $scope.removeNode = function(node) {
      if (node.parentNode == null) {
        //$scope.treeElements.splice($scope.treeElements.indexOf(node.node), 1);
        return;
      }
      node.parentNode.children.forEach(function(element) {
        if (element.name == node.node.name) {
          node.parentNode.children.splice(node.parentNode.children.indexOf(element), 1);
        }
      });
    };
    $scope.treeItemClass = '';
    $scope.addMode = {
      active: false,
    };
    //Enter "Add-mode" which shows a form
    //for adding a node to the map structure
    $scope.enterAddMode = function(node) {
      $scope.addMode.active = true;
      $('.tree-edit-item').draggable('disable');
    };
    //Exit add mode and return to default
    //map structure edit view
    $scope.exitAddMode = function() {
      $scope.addMode.active = false;
      $scope.treeItemClass = '';
      resetFormVariables();
      $('.tree-edit-item').draggable('enable');
    };
    $scope.updateMode = {
      node: null,
      active: false,
    };

    //Enter update mode which shows form for updating a node
    $scope.enterUpdateMode = function(node, parentNode) {
      if (parentNode == null) {
        alert('Root directory can not be updated');
        return;
      }
      if ($scope.updateMode.active && $scope.updateMode.node === node) {
        $scope.exitUpdateMode();
      } else {
        $scope.updateMode.active = true;
        vm.treeEditModel.name = node.name;
        vm.treeEditModel.type = node.type;
        vm.treeEditModel.use = node.use;
        $scope.updateMode.node = node;
        $('.tree-edit-item').draggable('disable');
      }
    };

    //Exit update mode and return to default map-structure editor
    $scope.exitUpdateMode = function() {
      $scope.updateMode.active = false;
      $scope.updateMode.node = null;
      $scope.selectedNode = null;
      $scope.currentNode = null;
      resetFormVariables();
      $('.tree-edit-item').draggable('enable');
    };
    //Resets add/update form fields
    function resetFormVariables() {
      vm.treeEditModel = {};
    }
    //Update current node variable with selected node in map structure tree view
    $scope.updateCurrentNode = function(node, selected, parentNode) {
      if (selected) {
        $scope.currentNode = {node: node, parentNode: parentNode};
      } else {
        $scope.currentNode = null;
      }
    };
    //Update node values
    $scope.updateNode = function(node) {
      if (vm.treeEditModel.name != '') {
        node.node.name = vm.treeEditModel.name;
      }
      if (vm.treeEditModel.type != '') {
        node.node.type = vm.treeEditModel.type;
      }
      if (vm.treeEditModel.use != '') {
        node.node.use = vm.treeEditModel.use;
      }
      $scope.exitUpdateMode();
    };
    //Select function for clicking a node
    $scope.showSelected = function(node, parentNode) {
      $scope.selectedNode = node;
      $scope.updateCurrentNode(node, $scope.selectedNode, parentNode);
      if ($scope.updateMode.active) {
        $scope.enterUpdateMode(node, parentNode);
      }
    };
    //Submit function for either Add or update
    $scope.treeEditSubmit = function(node) {
      if ($scope.addMode.active) {
        $scope.addNode(node);
      } else if ($scope.updateMode.active) {
        $scope.updateNode(node);
      }
    };
    //context menu data
    $scope.treeEditOptions = function(item) {
      if ($scope.addMode.active || $scope.updateMode.active) {
        return [];
      }
      return [
        [
          $translate.instant('ADD'),
          function($itemScope, $event, modelValue, text, $li) {
            $scope.showSelected($itemScope.node, $itemScope.$parentNode);
            $scope.enterAddMode($itemScope.node);
          },
        ],

        [
          $translate.instant('REMOVE'),
          function($itemScope, $event, modelValue, text, $li) {
            $scope.updateCurrentNode($itemScope.node, true, $itemScope.$parentNode);
            $scope.removeNode($scope.currentNode);
            $scope.selectedNode = null;
          },
        ],
        [
          $translate.instant('UPDATE'),
          function($itemScope, $event, modelValue, text, $li) {
            $scope.showSelected($itemScope.node, $itemScope.$parentNode);
            $scope.enterUpdateMode($itemScope.node, $itemScope.$parentNode);
          },
        ],
      ];
    };
  }
}
