/*
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2019 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
*/

export default class PrepareIpCtrl {
  constructor(
    IP,
    SA,
    Profile,
    $log,
    $uibModal,
    $timeout,
    $scope,
    $rootScope,
    listViewService,
    $translate,
    $controller
  ) {
    const vm = this;
    const ipSortString = ['Preparing'];
    const params = {
      package_type: 0,
    };
    $scope.angular = angular;
    $controller('BaseCtrl', {$scope: $scope, vm: vm, ipSortString: ipSortString, params});

    $scope.menuOptions = function(rowType, row) {
      const methods = [];
      methods.push({
        text: $translate.instant('INFORMATION_PACKAGE_INFORMATION'),
        click: function($itemScope, $event, modelValue, text, $li) {
          vm.ipInformationModal(row);
        },
      });
      return methods;
    };

    $scope.selectedProfileRow = {profile_type: '', class: ''};
    $scope.prepareAlert = null;
    $scope.setSelectedProfile = function(row) {
      $scope.selectRowCollection.forEach(function(profileRow) {
        if (profileRow.profile_type == $scope.selectedProfileRow.profile_type) {
          profileRow.class = '';
        }
      });
      if (row.profile_type == $scope.selectedProfileRow.profile_type && $scope.edit) {
        $scope.selectedProfileRow = {profile_type: '', class: ''};
      } else {
        row.class = 'selected';
        $scope.selectedProfileRow = row;
      }
    };

    $scope.$on('refresh_list_view', function() {
      $timeout(function() {
        $scope.getListViewData();
        $scope.ip.submission_agreement_locked = true;
      });
    });

    // Progress bar max value
    //funcitons for select view
    vm.profileModel = {};
    vm.profileFields = [];
    vm.options = {};
    //Click funciton for sa view
    $scope.saClick = function(row) {
      if ($scope.selectProfile == row && $scope.editSA) {
        $scope.editSA = false;
      } else {
        $scope.eventlog = false;
        $scope.edit = false;

        const chosen = row.profile;
        $scope.selectProfile = row;

        vm.profileFields = chosen.template;
        vm.profileOldModel = {};
        vm.profileModel = {};

        // only keep fields defined in template
        vm.profileFields.forEach(function(field) {
          vm.profileOldModel[field.key] = chosen[field.key];
          vm.profileModel[field.key] = chosen[field.key];
        });

        $scope.profileToSave = chosen;
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
        $scope.editSA = true;
      }
    };

    //Click funciton for profile view
    $scope.profileClick = function(row) {
      if ($scope.selectProfile == row && $scope.edit) {
        $scope.eventlog = false;
        $scope.edit = false;
      } else {
        $scope.editSA = false;
        $scope.closeAlert();
        let profileId;
        if (row.name) {
          profileId = row.id;
        } else {
          profileId = row.profile;
        }
        getAndShowProfile(profileId, row);
      }
    };

    function getAndShowProfile(profileId, row) {
      Profile.get({
        id: profileId,
        sa: $scope.saProfile.profile.id,
        ip: $scope.ip.id,
      }).$promise.then(function(resource) {
        resource.profile_name = resource.name;
        row.active = resource;
        row.profiles = [resource];
        $scope.selectProfile = row;
        vm.profileOldModel = row.active.specification_data;
        vm.profileModel = angular.copy(row.active.specification_data);
        vm.profileFields = row.active.template;
        $scope.treeElements = [{name: 'root', type: 'folder', children: angular.copy(row.active.structure)}];
        $scope.expandedNodes = [$scope.treeElements[0]].concat($scope.treeElements[0].children);
        $scope.profileToSave = row.active;
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

    //Include the given profile type in the SA
    $scope.includeProfileType = function(type) {
      const sendData = {
        type: type,
      };
      SA.includeType(angular.extend({id: $scope.saProfile.profile.id}, sendData)).$promise.then(
        function success(response) {},
        function error(response) {
          alert(response.status);
        }
      );
    };

    //Exclude the given profile type in the SA
    $scope.excludeProfileType = function(type) {
      const sendData = {
        type: type,
      };
      SA.excludeType(angular.extend({id: $scope.saProfile.profile.id}, sendData)).$promise.then(
        function success(response) {},
        function error(response) {
          alert(response.status);
        }
      );
    };
    //Make a profile "Checked"
    $scope.setCheckedProfile = function(type, checked) {
      IP.checkProfile({
        id: $scope.ip.id,
        type: type,
        checked: checked,
      }).$promise.then(
        function success(response) {},
        function error(response) {}
      );
    };

    $scope.optionalOptions = true;

    //Create and show modal for creating new ip
    $scope.newIpModal = function() {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/new-ip-modal.html',
        controller: 'PrepareIpModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {data: () => {}},
      });
      modalInstance.closed.then(function(data) {
        $scope.getListViewData();
        vm.updateListViewConditional();
      });
    };

    $scope.closeAlert = function() {
      $scope.lockAlert = null;
    };
    $scope.closePrepareAlert = function() {
      $scope.prepareAlert = null;
    };

    /*
     * Formly form  structure
     */
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
    function getStructure(profileId) {
      listViewService.getStructure(profileId).then(function(value) {
        $scope.treeElements = [{name: 'root', type: 'folder', children: value}];
        $scope.expandedNodes = [$scope.treeElements[0]].concat($scope.treeElements[0].children);
      });
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
      } else {
        return;
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

    vm.prepareIpForUploadModal = function(ip) {
      const ips = $scope.ips.length > 0 ? $scope.ips : null;
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/prepare_ip_for_upload_modal.html',
        scope: $scope,
        controller: 'DataModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: () => {
            return {
              ip: ip,
              ips: ips,
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $scope.getListViewData();
          $scope.ip = null;
          $rootScope.ip = null;
          $scope.ips = [];
          $scope.select = false;
          $scope.eventlog = false;
          $scope.edit = false;
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
  }
}
