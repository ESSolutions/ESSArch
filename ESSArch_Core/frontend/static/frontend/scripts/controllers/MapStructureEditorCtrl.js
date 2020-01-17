export default class MapStructureEditorCtrl {
  constructor($scope, $rootScope, $translate) {
    const vm = this;
    vm.noStructure = false;

    vm.$onInit = function() {
      if (vm.profile.structure.length == 0) {
        vm.useDefaultStructure();
      }
      $scope.treeElements = [{name: 'root', type: 'folder', children: vm.profile.structure}];
      $scope.expandedNodes = [$scope.treeElements[0]].concat($scope.treeElements[0].children);
    };
    vm.useDefaultStructure = function() {
      vm.noStructure = true;
      vm.profile.structure = [
        {
          type: 'file',
          name: 'mets.xml',
          use: 'mets_file',
        },
        {
          type: 'folder',
          name: 'content',
          children: [
            {
              type: 'file',
              name: 'mets_grp',
              use: 'mets_grp',
            },
            {
              type: 'folder',
              name: 'data',
              children: [],
            },
            {
              type: 'folder',
              name: 'metadata',
              children: [],
            },
          ],
        },
        {
          type: 'folder',
          name: 'metadata',
          children: [
            {
              type: 'file',
              use: 'xsd_files',
              name: 'xsd_files',
            },
            {
              type: 'file',
              name: 'premis.xml',
              use: 'preservation_description_file',
            },
            {
              type: 'file',
              name: 'ead.xml',
              use: 'archival_description_file',
            },
            {
              type: 'file',
              name: 'eac.xml',
              use: 'authoritive_information_file',
            },
          ],
        },
      ];
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
    //Generates test data for map structure tree
    function createSubTreeExampleData(level, width, prefix) {
      if (level > 0) {
        const res = [];
        // if (!parent) parent = res;
        for (let i = 1; i <= width; i++) {
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
