angular
  .module('essarch.controllers')
  .controller('ClassificationStructureEditorCtrl', function(
    $scope,
    $http,
    appConfig,
    Notifications,
    $uibModal,
    $log,
    $translate,
    Structure
  ) {
    var vm = this;
    vm.structure = null;
    vm.structures = [];
    vm.rules = {};
    $scope.angular = angular;
    vm.structureClick = function(row) {
      if (vm.structure && vm.structure.id === row.id) {
        vm.structure = null;
      } else {
        Structure.get({id: row.id}).$promise.then(function(resource) {
          vm.structure = resource;
          vm.oldStructure = angular.copy(resource);
          vm.getTree(vm.structure).then(function(tree) {
            vm.recreateTree(tree);
            vm.rules = vm.structure.specification.rules ? angular.copy(vm.structure.specification.rules) : {};
          });
        });
      }
    };

    vm.treeReady = function() {};

    vm.updateStructures = function() {
      vm.getStructures($scope.tableState);
    };

    vm.getStructures = function(tableState) {
      vm.structuresLoading = true;
      if (vm.structures.length == 0) {
        $scope.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        $scope.tableState = tableState;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        var sorting = tableState.sort;
        var pagination = tableState.pagination;
        var start = pagination.start || 0; // This is NOT the page number, but the index of item in the list that you want to use to display the table.
        var number = pagination.number || vm.structuresPerPage; // Number of entries showed per page.
        var pageNumber = start / number + 1;

        var sortString = sorting.predicate;
        if (sorting.reverse) {
          sortString = '-' + sortString;
        }
        Structure.query({
          page: pageNumber,
          page_size: number,
          ordering: sortString,
          search: search,
        }).$promise.then(function(resource) {
          vm.structures = resource;
          tableState.pagination.numberOfPages = Math.ceil(resource.$httpHeaders('Count') / number); //set the number of pages so the pagination can update
          $scope.initLoad = false;
          vm.structuresLoading = false;
        });
      }
    };

    // Tree

    vm.structureTreeData = [];
    var newId = 1;
    vm.ignoreStructureChanges = false;
    vm.newNode = {};

    vm.getTree = function(structure) {
      var rootNode = {
        text: structure.name,
        a_attr: {
          title: structure.name,
        },
        root: true,
        type: 'archive',
      };
      return $http
        .get(appConfig.djangoUrl + 'classification-structures/' + structure.id + '/tree/')
        .then(function(response) {
          var tree = response.data;
          if (tree.length <= 0) {
            return [rootNode];
          }
          tree.forEach(function(x) {
            prepareTree(x);
          });
          rootNode.children = tree;
          rootNode.state = {opened: true};
          var finalTree = [rootNode];
          return finalTree;
        })
        .catch(function(response) {
          return [rootNode];
        });
    };

    function prepareTree(current, depth) {
      current = createChild(current);
      if (current.children && current.children.length) {
        for (var i = 0; i < current.children.length; i++) {
          prepareTree(current.children[i], depth + 1);
        }
      }
    }

    createChild = function(child) {
      if (angular.isUndefined(child.name)) {
        child.name = '';
      }
      child.text = '<b>' + (child.reference_code ? child.reference_code : '') + '</b> ' + child.name;
      child.a_attr = {
        title: child.name,
      };
      child.original_parent = angular.copy(child.parent);
      delete child.parent;
      child.state = {opened: true};
      return child;
    };

    vm.structureTreeChange = function(jqueryobj, e) {
      if (e.action === 'select_node') {
      }
    };

    vm.expandChildren = function(jqueryobj, e, reload) {
      if (e.action === 'select node') {
        vm.node = e.node.original;
      }
    };

    function getNodeById(node, id) {
      var reduce = [].reduce;
      function runner(result, node) {
        if (result || !node) return result;
        return (
          (node._id === id && node) || //is this the proper node?
          runner(null, node.children) || //process this nodes children
          reduce.call(Object(node), runner, result)
        ); //maybe this is some ArrayLike Structure
      }
      return runner(null, node);
    }

    /**
     * Tree config for Record tree
     */
    vm.structureTreeConfig = {
      core: {
        multiple: false,
        animation: 50,
        error: function(error) {
          $log.error('treeCtrl: error from js tree - ' + angular.toJson(error));
        },
        check_callback: true,
        worker: true,
      },
      types: {
        default: {
          icon: 'far fa-folder',
        },
        archive: {
          icon: 'fas fa-archive',
        },
        document: {
          icon: 'far fa-file',
        },
        plus: {
          icon: 'fas fa-plus',
        },
      },
      contextmenu: {
        items: function(node, callback) {
          var update = {
            label: $translate.instant('UPDATE'),
            _disabled: node.original.root,
            action: function update() {
              vm.editNodeModal(node);
            },
          };
          var add = {
            label: $translate.instant('ADD'),
            action: function() {
              vm.addNodeModal(node.original, vm.structure);
            },
          };
          var remove = {
            label: $translate.instant('REMOVE'),
            _disabled: node.original.root,
            action: function() {
              vm.removeNodeModal(node, vm.structure);
            },
          };
          var actions = {
            update: update,
            add: add,
            remove: remove,
          };
          callback(actions);
          return actions;
        },
      },
      version: 1,
      plugins: ['types', 'contextmenu', 'dnd'],
    };

    vm.dropNode = function(jqueryObj, data) {
      var node = data.node.original;
      var parent = vm.structureTreeInstance.jstree(true).get_node(data.parent);
      $http({
        method: 'PATCH',
        url: appConfig.djangoUrl + 'classification-structures/' + vm.structure.id + '/units/' + node.id + '/',
        data: {
          parent: parent.original.id ? parent.original.id : '',
        },
      })
        .then(function(response) {})
        .catch(function(response) {
          Notifications.add('Could not be moved', 'error');
        });
    };

    vm.applyStructureModelChanges = function() {
      return !vm.ignoreStructureChanges;
    };

    vm.recreateTree = function(tags) {
      vm.ignoreStructureChanges = true;
      if (angular.equals(tags, vm.structureTreeData)) {
        vm.structureTreeConfig.version++;
      } else {
        vm.structureTreeData = angular.copy(tags);
        vm.structureTreeConfig.version++;
      }
    };

    // Rules
    vm.newRule = null;
    vm.addRule = function(name) {
      if (name !== null) {
        vm.rules[name] = {
          movable: true,
        };
        vm.newRule = null;
      }
    };
    vm.savingRules = false;
    vm.saveRules = function(rules, structure) {
      vm.savingRules = true;
      Structure.update(
        {
          id: structure.id,
        },
        {
          specification: {
            rules: rules,
          },
        }
      ).$promise.then(function(resource) {
        vm.structure = resource;
        vm.rules = resource.specification.rules ? angular.copy(resource.specification.rules) : {};
        vm.savingRules = false;
        Notifications.add($translate.instant('RULES_SAVED'), 'success');
      });
    };

    vm.savingSettings = false;
    vm.saveSettings = function(structure) {
      vm.savingSettings = true;
      Structure.update(
        {
          id: structure.id,
        },
        {
          start_date: vm.structure.start_date,
          end_date: vm.structure.end_date,
          level: vm.structure.level,
        }
      ).$promise.then(function(resource) {
        vm.structure = resource;
        vm.oldStructure = angular.copy(resource);
        vm.rules = resource.specification.rules ? angular.copy(resource.specification.rules) : {};
        vm.savingSettings = false;
        Notifications.add($translate.instant('SETTINGS_SAVED'), 'success');
      });
    };

    vm.removeRule = function(rule) {
      if (vm.rules[rule]) {
        delete vm.rules[rule];
      }
    };

    // Modals

    vm.editNodeModal = function(node) {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/edit_structure_unit_node_modal.html',
        controller: 'EditStructureUnitModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: {
            node: node.original,
            structure: vm.structure,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          vm.getTree(vm.structure).then(function(tree) {
            vm.recreateTree(tree);
          });
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    vm.addNodeModal = function(node, structure) {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/add_node_modal.html',
        controller: 'ClassificationModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: {
            node: node,
            structure: structure,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          vm.getTree(vm.structure).then(function(tree) {
            vm.recreateTree(tree);
          });
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.removeNodeModal = function(node, structure) {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_node_modal.html',
        controller: 'ClassificationModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: {
            node: node,
            structure: structure,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          vm.structureTreeInstance.jstree(true).delete_node(node.id);
          vm.structureTreeInstance.jstree(true).select_node(node.parent);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.removeStructureModal = function(structure) {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_structure_modal.html',
        controller: 'ClassificationModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: {
            structure: structure,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          vm.structure = null;
          vm.updateStructures();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.newStructureModal = function() {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/new_structure_modal.html',
        size: 'lg',
        controller: 'ClassificationModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {},
        },
      });
      modalInstance.result.then(
        function(data) {
          vm.updateStructures();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
  });
