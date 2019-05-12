angular
  .module('essarch.controllers')
  .controller('ProfileCtrl', function(
    $q,
    SA,
    Profile,
    $timeout,
    ProfileIp,
    ProfileIpData,
    $scope,
    $http,
    $rootScope,
    appConfig,
    listViewService,
    $log,
    $uibModal,
    $translate,
    $filter,
    IPReception
  ) {
    var vm = this;
    $scope.angular = angular;
    $scope.select = true;
    $scope.alerts = {
      receiveError: {type: 'danger', msg: $translate.instant('CANNOT_RECEIVE_ERROR')},
      aicDescriptionError: {type: 'danger', msg: $translate.instant('MISSING_AIC_DESCRIPTION')},
      aipError: {type: 'danger', msg: $translate.instant('MISSING_AIP')},
      dipError: {type: 'danger', msg: $translate.instant('MISSING_DIP')},
      aipDescriptionError: {type: 'danger', msg: $translate.instant('MISSING_AIP_DESCRIPTION')},
      noSas: {type: 'danger', msg: $translate.instant('NO_SUBMISSION_AGREEMENT_AVAILABLE')},
    };
    $scope.saAlert = null;
    $scope.aicDescriptionAlert = $scope.alerts.aicDescriptionError;
    $scope.aipAlert = $scope.alerts.aipError;
    $scope.dipAlert = $scope.alerts.dipError;
    $scope.aipDescriptionAlert = $scope.alerts.aipDescriptionError;
    vm.dataVersion = null;
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
      vm.cancel();
      vm.saCancel();
      vm.gettingSas = true;
      listViewService.getSaProfiles($scope.ip).then(function(result) {
        vm.gettingSas = false;
        $scope.saProfile.profiles = result.profiles;
        var chosen_sa_id = null;
        if ($scope.ip.submission_agreement) {
          chosen_sa_id = $scope.ip.submission_agreement;
        } else if ($scope.ip.altrecordids && $scope.ip.altrecordids.SUBMISSIONAGREEMENT) {
          chosen_sa_id = $scope.ip.altrecordids.SUBMISSIONAGREEMENT[0];
        }
        if (result.profiles.length <= 0) {
          $scope.saAlert = $scope.alerts.noSas;
        } else if (chosen_sa_id) {
          var found = $filter('filter')(result.profiles, {id: chosen_sa_id}, true);
          if (found.length) {
            $scope.saProfile.profile = found[0];
            $scope.saProfile.disabled = true;
          } else {
            $scope.saAlert = $scope.alerts.receiveError;
            $scope.saProfile.disabled = true;
            $scope.$emit('disable_receive', {});
          }
        }
        vm.shareData({
          $event: {
            approved: false,
            aipProfileId: $scope.saProfile.profile.profile_aip.id,
            dipProfileId: $scope.saProfile.profile.profile_dip.id,
            aipModel: vm.savedAip,
            dipModel: vm.savedDip,
            submissionAgreement: $scope.saProfile.profile.id,
            saObject: $scope.saProfile.profile,
          },
        });
        vm.loadProfiles($scope.ip);
      });
    }

    vm.loadProfiles = function(ip) {
      $scope.selectRowCollapse = [];
      return ProfileIp.query({ip: ip.id}).$promise.then(function(resource) {
        resource.forEach(function(profileIp) {
          $scope.selectRowCollapse.push(profileIp);
        });
        $scope.selectRowCollection = $scope.selectRowCollapse;
        return $scope.selectRowCollection;
      });
    };

    vm.changeDataVersion = function(profileIp, data) {
      ProfileIp.patch({id: profileIp.id}, {data: data}).$promise.then(function(resource) {
        ProfileIp.get({id: resource.id}).$promise.then(function(response) {
          vm.profileIp = response;
          vm.loadProfiles($scope.ip);
          vm.getAndShowProfile(vm.profileIp, {});
        });
      });
    };

    $scope.pushData = function() {
      vm.shareData({
        $event: {
          approved: true,
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
              vm.loadProfiles($scope.ip);
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
    };
    vm.profileModel = {};
    vm.profileFields = [];
    vm.options = {};
    //Click funciton for sa view
    $scope.saClick = function(row) {
      vm.loadingSa = true;
      if ($scope.selectedSa == row && $scope.editSA) {
        vm.loadingSa = false;
        vm.saCancel();
        $scope.editSA = false;
      } else {
        $scope.selectedSa = row;
        $scope.eventlog = false;
        $scope.edit = false;

        var chosen = row.profile;

        vm.saFields = [];
        vm.saModel = {};

        // only keep fields defined in template
        chosen.template.forEach(function(field) {
          if (!field.hidden) {
            vm.saModel[field.key] = chosen[field.key];
            vm.saFields.push(field);
          }
        });
        var toDelete = [];
        vm.saFields = vm.saFields.map(function(field, idx) {
          delete field.templateOptions.options;
          field.type = 'input';
          field.templateOptions.disabled = true;
          if (field.key.startsWith('profile_')) {
            $scope.selectRowCollection.forEach(function(profile) {
              if (vm.saModel[field.key] == profile.id) {
                vm.saModel[field.key] = profile.name;
              }
            });
            if (vm.saModel[field.key] == null) {
              toDelete.push(field);
            }
            field.templateOptions.label = field.key.replace('profile_', '');
          }
          return field;
        });
        toDelete.forEach(function(field) {
          vm.saFields.splice(vm.saFields.indexOf(field), 1);
        });
        vm.loadingSa = false;
        $scope.editSA = true;
      }
    };

    //Click funciton for profile view
    $scope.profileClick = function(row) {
      if (vm.selectedProfile && vm.selectedProfile.id == row.id) {
        $scope.eventlog = false;
        $scope.edit = false;
        vm.cancel();
      } else {
        $scope.editSA = false;
        vm.cancel();
        $timeout(function() {
          vm.getAndShowProfile(row, {});
          $scope.edit = true;
        });
      }
    };

    vm.fieldsLoading = function() {
      var val = false;
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
    vm.getAndShowProfile = function(profileIp, row) {
      vm.loadingProfileData[profileIp.profile_type] = true;
      vm.selectedProfile = profileIp;
      vm.profileIp = profileIp;
      Profile.get({
        id: profileIp.profile,
      })
        .$promise.then(function(resource) {
          resource.profile_name = resource.name;
          row.active = resource;
          row.profiles = [resource];
          $scope.selectProfile = row;
          if (profileIp.data == null) {
            profileIp.data = {data: {}};
          }
          vm.profileOldModel = angular.copy(profileIp.data.data);
          vm.profileModel = angular.copy(profileIp.data.data);
          vm.dataVersion = profileIp.data_versions[profileIp.data_versions.indexOf(profileIp.data.id)];
          getStructure(row.active);
          $scope.profileToSave = row.active;
          vm.profileFields = row.active.template;
          $scope.edit = true;
          $scope.eventlog = true;
          vm.loadingProfileData[profileIp.profile_type] = false;
        })
        .catch(function(response) {
          vm.loadingProfileData[profileIp.profile_type] = false;
          vm.cancel();
        });
    };

    vm.getProfileData = function(id) {
      ProfileIpData.get({id: id}).$promise.then(function(resource) {
        vm.profileModel = angular.copy(resource.data);
      });
    };
    //Gets all submission agreement profiles
    $scope.getSaProfiles = function(ip) {
      listViewService.getSaProfiles(ip).then(function(value) {
        $scope.saProfile = value;
      });
    };

    //Create and show modal when saving an SA
    vm.saveSAModal = function() {
      if (vm.editForm.$valid) {
        vm.options.updateInitialValue();
        var modalInstance = $uibModal.open({
          animation: true,
          ariaLabelledBy: 'modal-title',
          ariaDescribedBy: 'modal-body',
          templateUrl: 'static/frontend/views/save_sa_modal.html',
          controller: 'ModalInstanceCtrl',
          controllerAs: '$ctrl',
        });
        modalInstance.result.then(
          function(data) {
            vm.onSASubmit(data.name);
          },
          function() {
            $log.info('modal-component dismissed at: ' + new Date());
          }
        );
      }
    };

    //Create and show modal when saving a profile
    vm.saveModal = function() {
      if (vm.editForm.$valid) {
        vm.options.updateInitialValue();
        var modalInstance = $uibModal.open({
          animation: true,
          ariaLabelledBy: 'modal-title',
          ariaDescribedBy: 'modal-body',
          templateUrl: 'static/frontend/views/enter-profile-name-modal.html',
          controller: 'ModalInstanceCtrl',
          controllerAs: '$ctrl',
        });
        modalInstance.result.then(
          function(data) {
            vm.onSubmit(data.name);
          },
          function() {
            $log.info('modal-component dismissed at: ' + new Date());
          }
        );
      }
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
        $scope.expandedNodes = [$scope.treeElements[0]].concat($scope.treeElements[0].children);
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

    // Map for profile types
    var typeMap = {
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
          options: [{name: 'folder', value: 'folder'}, {name: 'file', value: 'file'}],
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
    //Generates test data for map structure tree
    function createSubTreeExampleData(level, width, prefix) {
      if (level > 0) {
        var res = [];
        // if (!parent) parent = res;
        for (var i = 1; i <= width; i++) {
          res.push({
            name: 'Node ' + prefix + i,
            type: 'folder',
            children: createSubTreeExampleData(level - 1, width, prefix + i + '.'),
          });
        }

        return res;
      } else return [];
    }
    //Populate map structure tree view given tree width and amount of levels
    function getStructure(profile) {
      $scope.treeElements = [{name: 'root', type: 'folder', children: profile.structure}];
      $scope.expandedNodes = [$scope.treeElements[0]].concat($scope.treeElements[0].children);
    }
    $scope.treeElements = []; //[{name: "Root", type: "Folder", children: createSubTree(3, 4, "")}];
    $scope.currentNode = null;
    $scope.selectedNode = null;
    //Add node to map structure tree view
    $scope.addNode = function(node) {
      var dir = {
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

    $scope.prepare = function(ip) {
      vm.preparingIp = true;
      return IPReception.prepare({id: ip.id, submission_agreement: $scope.saProfile.profile.id})
        .$promise.then(function(resource) {
          vm.preparingIp = false;
          vm.ip = resource;
          $scope.$emit('update_ip', {ip: resource});
          return resource;
        })
        .catch(function(response) {
          vm.preparingIp = false;
        });
    };
  });
