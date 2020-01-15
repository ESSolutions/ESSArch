import get from 'lodash/get';

export default class SearchDetailCtrl {
  constructor(
    $scope,
    $controller,
    $stateParams,
    Search,
    $q,
    $http,
    $rootScope,
    appConfig,
    $log,
    Notifications,
    $sce,
    $translate,
    $uibModal,
    PermPermissionStore,
    $window,
    $state,
    $interval,
    StructureName,
    AgentName,
    $transitions,
    StructureUnitRelation
  ) {
    const PAGE_SIZE = 10;

    const vm = this;
    $controller('TagsCtrl', {$scope: $scope, vm: vm});
    $scope.StructureName = StructureName;
    $scope.angular = angular;
    $scope.StructureUnitRelation = StructureUnitRelation;
    vm.url = appConfig.djangoUrl;
    vm.unavailable = false;
    vm.structure = null;
    vm.recordTreeData = [];
    vm.idCopied = false;

    // Record update interval
    let recordInterval;

    // Destroy intervals on state change
    $transitions.onSuccess({}, function($transition) {
      $interval.cancel(recordInterval);
    });

    vm.$onInit = function() {
      if ($stateParams.structure) {
        vm.loadRecordAndTree($stateParams.structure);
      } else {
        vm.loadRecordAndTree();
      }
    };

    vm.idCopyDone = function() {
      vm.idCopied = true;
    };

    vm.structureChanged = structure => {
      if (structure !== null) {
        vm.loadRecordAndTree(structure);
      }
    };

    vm.loadRecordAndTree = function(structure) {
      const isStructureUnit = $state.current.name == 'home.archivalDescriptions.search.structure_unit';
      const nodeId = $stateParams.id;

      if (isStructureUnit) {
        console.log('Getting data for initial node, structure unit -', nodeId);
        var nodePromise = vm.getStructureUnit(nodeId);
      } else {
        console.log('Getting data for initial node, tag -', nodeId);
        var nodePromise = vm.getNode(nodeId);
      }

      nodePromise.then(function(data) {
        data.state = {selected: true, opened: true};
        vm.sortNotes(data);
        vm.record = data;
        if (!vm.record._is_structure_unit) {
          vm.parseAgents(vm.record);
        }
        const startNode = data;
        let archiveId = null;

        $rootScope.$broadcast('UPDATE_TITLE', {title: vm.record.name});

        if (!data._is_structure_unit) {
          vm.currentVersion = vm.record._id;
          getVersionSelectData();

          archiveId = data.root;
        } else {
          archiveId = vm.record.archive;
        }
        vm.structureId = structure ? structure : vm.record.structure;

        if (vm.record._id === archiveId) {
          vm.createArchiveNode(startNode, vm.record);
        } else {
          if (!angular.isUndefined(archiveId) && archiveId !== null) {
            console.log('Initial node is not its own archive, getting archive:', archiveId);
            vm.getNode(archiveId).then(function(archive) {
              vm.createArchiveNode(startNode, archive);
            });
          }
        }
      });
    };

    vm.createArchiveNode = function(startNode, archive) {
      delete archive.parent;
      vm.archive = archive;
      vm.archiveStructures = angular.copy(archive.structures);
      vm.structure = vm.getStructureById(vm.archiveStructures, vm.structureId);

      if (!vm.structure && vm.record.structures.length > 0) {
        vm.structure = vm.record.structures[vm.record.structures.length - 1];
      }

      vm.buildTree(startNode, archive).then(function(children) {
        archive.children = children.data;
        vm.parseAgents(archive);
        let creator = vm.getArchiveCreator(archive);

        if (creator !== null) {
          creator._id = creator.id;
          creator = vm.createNode(creator);
          creator.children = [angular.copy(archive)];
          var tree = [creator];
        } else {
          var tree = [archive];
        }

        vm.ignoreRecordChanges = true;
        if (!angular.equals(tree, vm.recordTreeData)) {
          angular.copy(tree, vm.recordTreeData);
        }
        vm.recordTreeConfig.version++;
      });
    };

    vm.createNode = function(node) {
      if (angular.isUndefined(node.name)) {
        node.name = '';
      }
      if (node._is_structure_unit !== true) {
        node.id = node._id;
      }

      if (node._is_structure_unit !== true) {
        node.reference_code = node.reference_code || '';
      }

      node.text = '<b>' + node.reference_code + '</b> ' + node.name;
      node.a_attr = {
        title: node.name,
      };
      if (!node.is_leaf_node) {
        node.children = [vm.createPlaceholderNode()];
      }
      node.state = {opened: false};
      return node;
    };

    vm.getNode = function(id) {
      const structureId = vm.structure ? vm.structure.id : vm.structureId;
      return $http.get(vm.url + 'search/' + id + '/', {params: {structure: structureId}}).then(function(response) {
        response.data._is_structure_unit = false;
        return vm.createNode(response.data);
      });
    };

    vm.getStructureUnit = function(id) {
      return $http.get(vm.url + 'structure-units/' + id + '/').then(function(response) {
        response.data._id = response.data.id;
        response.data._is_structure_unit = true;
        return vm.createNode(response.data);
      });
    };

    vm.getParent = function(childNode) {
      console.log('Getting parent of', childNode);
      if (childNode.structure_unit) {
        return vm.getStructureUnit(childNode.structure_unit.id);
      } else if (childNode.parent) {
        if (childNode._is_structure_unit) {
          return vm.getStructureUnit(childNode.parent);
        }
        return vm.getNode(childNode.parent.id);
      } else {
        const deferred = $q.defer();
        deferred.resolve(null);
        return deferred.promise;
      }
    };

    vm.getChildren = function(node, archive, page) {
      let url;
      const params = {page_size: PAGE_SIZE, page: page || 1};

      if (node._is_structure_unit === true) {
        url = vm.url + 'structure-units/' + node._id + '/children/';
      } else if (node._id === vm.archive._id) {
        return vm.getClassificationStructureChildren(vm.structure.id);
      } else {
        url = vm.url + 'search/' + node._id + '/children/';
        params.structure = vm.structure.id;
      }

      console.log('Getting children to', node, 'in archive', archive._id);
      return $http.get(url, {params: params}).then(function(response) {
        const data = response.data.map(function(child) {
          child._is_structure_unit = node._is_structure_unit && !node.is_unit_leaf_node;
          if (angular.isUndefined(child._id)) {
            child._id = child.id;
          }
          delete child.parent;
          return vm.createNode(child);
        });

        const count = response.headers('Count');
        console.log('Found', count, 'children to', node, 'in archive', archive._id);
        return {
          data: data,
          count: count,
        };
      });
    };

    vm.getClassificationStructureChildren = function(id) {
      console.log('Getting children of structure with id "' + id + '"');
      const url = vm.url + 'structures/' + id + '/units/';
      return $http.get(url, {params: {has_parent: false, pager: 'none'}}).then(function(response) {
        const data = response.data.map(function(unit) {
          unit._id = unit.id;
          unit._is_structure_unit = true;
          delete unit.parent;
          return vm.createNode(unit);
        });
        return {
          data: data,
          count: response.headers('Count'),
        };
      });
    };

    vm.createPlaceholderNode = function() {
      return {
        text: '',
        placeholder: true,
        icon: false,
        state: {disabled: true},
      };
    };

    vm.createSeeMoreNode = function() {
      return {
        text: $translate.instant('ACCESS.SEE_MORE'),
        see_more: true,
        state: {checkbox_disabled: true},
        type: 'plus',
        _source: {},
      };
    };

    vm.buildTree = function(start, archive) {
      console.log('Building tree of', start, 'with archive', archive._id);
      return vm.getChildren(start, archive).then(function(children) {
        const existingChild =
          start.children && start.children.length > 0 && start.children[0].placeholder !== true
            ? start.children[0]
            : null;

        start.children = [];
        children.data.forEach(function(child) {
          if (existingChild === null || existingChild._id !== child._id) {
            start.children.push(child);
          } else if (existingChild !== null && existingChild._id === child._id) {
            start.children.push(existingChild);
          }
        });

        if (start.children.length < children.count) {
          start.children.push(vm.createSeeMoreNode());
          if (existingChild && !getNodeById(start, existingChild._id)) {
            start.state.opened = true;
            start.children.push(existingChild);
          }
        }

        return vm.getParent(start).then(function(parent) {
          delete start.parent;

          if (parent !== null) {
            parent.children = [start];
            parent.state = {opened: true};
            return vm.buildTree(parent, archive, vm.structure.id);
          } else {
            return vm.getClassificationStructureChildren(vm.structure.id).then(function(children) {
              const result = [];
              children.data.forEach(function(child) {
                if (start._id === child._id) {
                  result.push(start);
                } else {
                  result.push(child);
                }
              });

              return {
                data: result,
                count: children.count,
              };
            });
          }
        });
      });
    };

    vm.selectRecord = function(jqueryobj, e) {
      if (e.node && e.node.original.see_more) {
        const tree = vm.recordTreeData;
        const parent = vm.recordTreeInstance.jstree(true).get_node(e.node.parent);
        const childrenNodes = tree.map(function(x) {
          return getNodeById(x, parent.original._id);
        })[0].children;
        const page = Math.ceil(childrenNodes.length / PAGE_SIZE);

        return vm.getChildren(parent.original, vm.archive, page).then(function(children) {
          const count = children.count;
          let selectedElement = null;
          let seeMore = null;

          if (childrenNodes[childrenNodes.length - 1].see_more) {
            seeMore = childrenNodes.pop();
            vm.recordTreeInstance.jstree(true).delete_node(e.node.id);
          } else {
            selectedElement = childrenNodes.pop();
            vm.recordTreeInstance.jstree(true).delete_node(parent.children[parent.children.length - 1]);
            seeMore = childrenNodes.pop();
            vm.recordTreeInstance.jstree(true).delete_node(e.node.id);
          }
          children.data.forEach(function(child) {
            if (selectedElement !== null && child._id === selectedElement._id) {
              child = selectedElement;
            } else {
              child = vm.createNode(child);
            }
            childrenNodes.push(child);
            vm.recordTreeInstance.jstree(true).create_node(parent.id, angular.copy(child));
          });

          if (childrenNodes.length < count) {
            childrenNodes.push(seeMore);
            vm.recordTreeInstance.jstree(true).create_node(parent.id, seeMore);
          }
        });
      } else if (e.node.original.type === 'agent') {
        $state.go('home.archivalDescriptions.archiveCreators', {id: e.node.original.id});
      } else {
        if (e.node.original._id !== vm.record._id) {
          vm.goToNode(e.node.id);
        }
      }
    };

    vm.goToNode = function(id) {
      const tree = vm.recordTreeInstance.jstree(true);
      const node = tree.get_node(id);

      if (node.original.type === 'agent') {
        $state.go('home.archivalDescriptions.archiveCreators', {id: node.original.id});
        return;
      }

      if (node.original._is_structure_unit != vm.record._is_structure_unit) {
        vm.goToNodePage(id, node.original._is_structure_unit);
        return;
      }

      const nodePromise = node.original._is_structure_unit
        ? vm.getStructureUnit(node.original._id)
        : vm.getNode(node.original._id);
      tree.deselect_node(vm.record.id);
      tree.select_node(node);
      nodePromise.then(function(node) {
        vm.sortNotes(node);
        vm.record = node;
        if (!vm.record._is_structure_unit) {
          vm.parseAgents(vm.record);
        }
        vm.getChildren(vm.record, vm.archive).then(function(children) {
          vm.record.children = children.data;
        });
        $rootScope.latestRecord = node;
        if (vm.record._is_structure_unit)
          $state.go(
            'home.archivalDescriptions.search.structure_unit',
            {id: vm.record._id, archive: vm.archive._id},
            {notify: false}
          );
        else {
          $state.go('home.archivalDescriptions.search.' + vm.record._index, {id: vm.record._id}, {notify: false});
          getVersionSelectData();
        }
        $rootScope.$broadcast('UPDATE_TITLE', {title: vm.record.name});

        vm.currentVersion = vm.record._id;
        vm.record.breadcrumbs = getBreadcrumbs(vm.record);

        vm.getChildrenTable(vm.recordTableState);
        vm.getTransfers({pager: 'none'});
      });
    };

    vm.goToNodePage = function(id, isStructureUnit) {
      if (isStructureUnit)
        $state.go(
          'home.archivalDescriptions.search.structure_unit',
          {id: id, archive: vm.archive._id, structure: vm.structure.id},
          {notify: true}
        );
      else {
        $state.go('home.archivalDescriptions.search.component', {id: id, structure: vm.structure.id}, {notify: true});
      }
    };

    vm.getChildrenTable = function(tableState) {
      if (!angular.isUndefined(tableState)) {
        vm.recordTableState = tableState;
        const pagination = tableState.pagination;
        const start = pagination.start || 0; // This is NOT the page number, but the index of item in the list that you want to use to display the table.
        const pageSize = pagination.number || PAGE_SIZE; // Number of entries showed per page.
        const pageNumber = start / pageSize + 1;

        vm.childrenLoading = true;
        vm.getChildren(vm.record, vm.archive, pageNumber).then(function(result) {
          vm.childrenLoading = false;
          vm.recordChildren = result.data;
          tableState.pagination.numberOfPages = Math.ceil(result.count / pageSize);
        });
      }
    };

    vm.currentItem = null;
    vm.structureUnits = null;
    vm.archive = null;
    vm.rootNode = null;

    vm.transfers = [];
    vm.getTransfers = function(tableState) {
      vm.transferTableState = tableState;
      let url = 'search/';
      if (vm.record._is_structure_unit) {
        url = 'structure-units/';
      }
      return $http
        .get(appConfig.djangoUrl + url + vm.record.id + '/transfers/', {params: {pager: 'none'}})
        .then(function(response) {
          vm.transfers = response.data;
          return response.data;
        });
    };

    $scope.checkPermission = function(permissionName) {
      return !angular.isUndefined(PermPermissionStore.getPermissionDefinition(permissionName));
    };

    vm.existsForRecord = function(classification) {
      if (vm.record) {
        if (vm.record.structures) {
          let temp = false;
          vm.record.structures.forEach(function(structure) {
            if (structure.id === classification) {
              temp = true;
            }
          });
          return temp;
        } else if (vm.record.structure) {
          return vm.record.structure === classification;
        }
      }
    };

    function getBreadcrumbs(node) {
      const tree = vm.recordTreeInstance.jstree(true);
      const start = tree.get_node(node.id);

      if (start === false) {
        return [];
      }

      return tree.get_path(start, false, true).map(function(id) {
        return tree.get_node(id).original;
      });
    }

    vm.ignoreChanges = false;
    vm.ignoreRecordChanges = false;
    vm.newNode = {};

    vm.applyRecordModelChanges = function() {
      return !vm.ignoreRecordChanges;
    };

    /**
     * Tree config for Record tree
     */
    vm.recordTreeConfig = {
      core: {
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
        agent: {
          icon: 'fas fa-user',
        },
      },
      dnd: {
        is_draggable: function(nodes) {
          const not_draggable = nodes.some(function(node) {
            return (
              (node.original._is_structure_unit &&
                !(
                  $scope.checkPermission('tags.move_structureunit_instance') &&
                  vm.structure.type.movable_instance_units
                )) ||
              node.original._index === 'archive'
            );
          });
          if (not_draggable) {
            return false;
          }

          let structure = null;
          vm.archiveStructures.forEach(function(struct) {
            if (struct.id === vm.structure.id) {
              structure = struct;
            }
          });
          const type = nodes[0].original.type;
          return get(structure, 'specification.rules.' + type + '.movable', true);
        },
      },
      contextmenu: {
        select_node: false,
        items: function(node, callback) {
          const update = {
            label: $translate.instant('EDIT'),
            _disabled: function() {
              return (
                node.original._is_structure_unit &&
                !(
                  $scope.checkPermission('tags.change_structureunit_instance') && vm.structure.type.editable_instances
                ) &&
                !(!node.original._is_structure_unit && $scope.checkPermission('tags.change_tagversion'))
              );
            },
            action: function update() {
              if (node.original._is_structure_unit) {
                const struct = vm.structure;
                struct.structureType = angular.copy(struct.type);
                vm.editStructureUnitModal(node.original, struct);
              } else if (node.original._index === 'archive') {
                vm.editArchiveModal(node.original);
              } else {
                vm.editNodeModal(node.original);
              }
            },
          };
          const add = {
            label: $translate.instant('ACCESS.ADD_NODE'),
            _disabled: function() {
              return node.original._index === 'archive' || !$scope.checkPermission('tags.add_tag');
            },
            action: function() {
              vm.addNodeModal(node, vm.structure.id);
            },
          };
          const addStructureUnit = {
            label: $translate.instant('ACCESS.ADD_STRUCTURE_UNIT'),
            _disabled: function() {
              return !(
                $scope.checkPermission('tags.add_structureunit_instance') && vm.structure.type.editable_instances
              );
            },
            action: function() {
              const struct = vm.structure;
              struct.structureType = angular.copy(struct.type);
              vm.addStructureUnitModal(node.original, struct);
            },
          };
          const remove = {
            label: $translate.instant('REMOVE'),
            _disabled: function() {
              return (
                (node.original._is_structure_unit &&
                  !(
                    $scope.checkPermission('tags.delete_structureunit_instance') &&
                    vm.structure.type.editable_instances
                  )) ||
                node.original._index === 'archive' ||
                !$scope.checkPermission('tags.delete_tagversion')
              );
            },
            action: function() {
              if (node.original._is_structure_unit) {
                const struct = vm.structure;
                struct.structureType = angular.copy(struct.type);
                vm.removeStructureUnitModal(node, struct);
              } else {
                vm.removeNodeModal(node);
              }
            },
          };
          const addLocation = {
            label: $translate.instant('ACCESS.LINK_TO_LOCATION'),
            _disabled: function() {
              return !$scope.checkPermission('tags.change_tag_location');
            },
            action: function() {
              vm.addNodeLocationModal(node.original);
            },
          };
          const addDelivery = {
            label: $translate.instant('ACCESS.LINK_TO_TRANSFER'),
            _disabled: function() {
              return !$scope.checkPermission('tags.change_transfer');
            },
            action: function() {
              vm.addNodeDeliveryModal(node.original);
            },
          };
          const removeFromStructure = {
            label: $translate.instant('ACCESS.REMOVE_FROM_CLASSIFICATION_STRUCTURE'),
            _disabled: function() {
              return (
                node.original._is_structure_unit ||
                node.original._index === 'archive' ||
                !$scope.checkPermission('tags.change_classification')
              );
            },
            action: function() {
              let struct;
              vm.archiveStructures.forEach(function(item) {
                if (item.id === vm.structure.id) {
                  struct = item;
                }
              });
              vm.removeNodeFromStructureModal(node, struct);
            },
          };
          const newVersion = {
            label: $translate.instant('ACCESS.NEW_VERSION'),
            _disabled: function() {
              return node.original._is_structure_unit;
            },
            action: function() {
              vm.newVersionNodeModal(node);
            },
          };
          const changeOrganization = {
            label: $translate.instant('ORGANIZATION.CHANGE_ORGANIZATION'),
            _disabled: function() {
              return node.original._index !== 'archive';
            },
            action: function() {
              vm.changeOrganizationModal(node.original);
            },
          };
          const email = {
            label: $translate.instant('EMAIL.EMAIL'),
            _disabled: function() {
              return node.original._is_structure_unit;
            },
            action: function() {
              const selected = vm.recordTreeInstance
                .jstree(true)
                .get_selected(true)
                .map(function(x) {
                  return x.original;
                });
              if (selected.length > 1) {
                Search.massEmail(selected)
                  .then(function(response) {
                    Notifications.add($translate.instant('EMAILS_SENT'), 'success');
                  })
                  .catch(function(response) {
                    if (response.status !== 500) {
                      Notifications.add($translate.instant('EMAILS_FAILED'), 'error');
                    }
                  });
              } else if (selected.length == 1) {
                vm.emailDocument(selected[0]);
              }
            },
          };
          const isUnit = node.original._is_structure_unit;
          const isUnitLeaf = node.original.is_unit_leaf_node;
          const isLeaf = node.original.is_leaf_node;
          const actions =
            node.original.type === 'agent'
              ? {}
              : {
                  update: update,
                  add: !isUnit || isUnitLeaf ? add : undefined,
                  addStructureUnit:
                    (isUnit && isUnitLeaf === isLeaf) || node.original._index === 'archive'
                      ? addStructureUnit
                      : undefined,
                  email: email,
                  remove: remove,
                  addLocation: !isUnit && node.original._index !== 'archive' ? addLocation : null,
                  addDelivery: addDelivery,
                  removeFromStructure: removeFromStructure,
                  newVersion: newVersion,
                  changeOrganization: changeOrganization,
                };
          callback(actions);
          return actions;
        },
      },
      checkbox: {
        whole_node: false,
        tie_selection: false,
        visible: true,
        three_state: false,
      },
      version: 1,
      plugins: ['types', 'contextmenu', 'dnd', 'checkbox'],
    };

    vm.getChecked = function() {
      return vm.recordTreeInstance
        .jstree(true)
        .get_checked()
        .map(function(x) {
          return vm.recordTreeInstance.jstree(true).get_node(x).original;
        });
    };

    vm.locationButtonDisabled = function() {
      const checked = vm.getChecked();
      let disabled = true;
      checked.forEach(function(x) {
        if (
          !angular.isUndefined(x) &&
          x._is_structure_unit !== true &&
          x._index !== 'archive' &&
          x.placeholder !== true &&
          x.type !== 'agent'
        ) {
          disabled = false;
        }
      });
      return disabled;
    };

    vm.deliveryButtonDisabled = function() {
      const checked = vm.getChecked();
      let disabled = true;
      checked.forEach(function(x) {
        if (!angular.isUndefined(x) && x.placeholder !== true && x.type !== 'agent') {
          disabled = false;
        }
      });
      return disabled;
    };

    vm.gotoNode = function(node) {
      $state.go('home.archivalDescriptions.search.' + node._index, {id: node._id});
    };

    vm.dropNode = function(jqueryObj, data) {
      const node = data.node;
      const parentNode = vm.recordTreeInstance.jstree(true).get_node(node.parent);
      if (vm.checkDroppable(node, parentNode)) {
        var data = {structure: vm.structure.id};

        if (parentNode.original._is_structure_unit && !node.original._is_structure_unit) {
          data.structure_unit = parentNode.id;
        } else if (parentNode.original._index === 'archive') {
          data.parent = null;
        } else {
          data.parent = parentNode.id;
        }

        let promise;
        $rootScope.skipErrorNotification = true;
        if (node.original._is_structure_unit) {
          promise = Search.updateStructureUnit(node.original, data, true);
        } else {
          promise = Search.updateNode(node.original, data, true);
        }

        promise
          .then(() => {
            vm.loadRecordAndTree(vm.structure.id);
          })
          .catch(() => {
            vm.loadRecordAndTree(vm.structure.id);
            Notifications.add($translate.instant('ACCESS.COULD_NOT_BE_MOVED'), 'error');
          });
      } else {
        vm.loadRecordAndTree(vm.structure.id);
        Notifications.add($translate.instant('ACCESS.COULD_NOT_BE_MOVED'), 'error');
      }
    };

    vm.checkDroppable = (src, dst) => {
      let droppable = true;
      if (src.original._is_structure_unit) {
        if (!dst.original._is_structure_unit && dst.original._index !== 'archive') {
          droppable = false;
        }
        if (dst.original._is_structure_unit && !dst.original.is_tag_leaf_node) {
          droppable = false;
        }
      } else {
        if (dst.original._is_structure_unit && !dst.original.is_unit_leaf_node) {
          droppable = false;
        }
      }
      return droppable;
    };

    vm.setType = function() {
      if (vm.record) {
        vm.record.breadcrumbs = getBreadcrumbs(vm.record);
      }

      vm.recordTreeInstance
        .jstree(true)
        .get_json('#', {flat: true})
        .forEach(function(item) {
          const fullItem = vm.recordTreeInstance.jstree(true).get_node(item.id);
          if (fullItem.original._index == 'archive') {
            vm.recordTreeInstance.jstree(true).set_type(item, 'archive');
          }
        });
    };

    vm.treeChange = function(jqueryobj, e) {
      if (e.action === 'select_node') {
        vm.selectRecord(jqueryobj, e);
      }
    };

    function getVersionSelectData() {
      vm.currentVersion = vm.record._id;
      vm.record.versions.push(angular.copy(vm.record));
      vm.record.versions.sort(function(a, b) {
        const a_date = new Date(a.create_date),
          b_date = new Date(b.create_date);
        if (a_date < b_date) return -1;
        if (a_date > b_date) return 1;
        return 0;
      });
    }

    vm.expandChildren = function(jqueryobj, e, reload) {
      const tree = vm.recordTreeData;
      if (e.node.children.length < 2 || reload) {
        const childrenNodes = tree.map(function(x) {
          return getNodeById(x, e.node.original._id);
        })[0].children;
        const page = Math.ceil(childrenNodes.length / PAGE_SIZE);

        if (e.node.original.type === 'agent') {
          return null;
        }
        return vm.getChildren(e.node.original, vm.archive, page).then(function(children) {
          const count = children.count;
          let selectedElement = null;
          let seeMore = null;

          if (childrenNodes[childrenNodes.length - 1].see_more) {
            seeMore = childrenNodes.pop();
            vm.recordTreeInstance.jstree(true).delete_node(e.node.id);
          } else {
            selectedElement = childrenNodes.pop();
            vm.recordTreeInstance.jstree(true).delete_node(e.node.children[e.node.children.length - 1]);
            if (childrenNodes.length > 0 && childrenNodes[childrenNodes.length - 1].see_more) {
              seeMore = childrenNodes.pop();
            } else {
              seeMore = vm.createSeeMoreNode();
            }
          }
          children.data.forEach(function(child) {
            if (selectedElement !== null && child._id === selectedElement._id) {
              child = selectedElement;
            } else {
              child = vm.createNode(child);
            }
            childrenNodes.push(child);
            vm.recordTreeInstance.jstree(true).create_node(e.node.id, angular.copy(child));
          });

          if (childrenNodes.length < count) {
            childrenNodes.push(seeMore);
            vm.recordTreeInstance.jstree(true).create_node(e.node.id, seeMore);
          }
        });
      }
    };

    function getNodeById(node, id) {
      const reduce = [].reduce;
      function runner(result, node) {
        if (result || !node) return result;
        return (node._id === id && node) || runner(null, node.children) || reduce.call(Object(node), runner, result);
      }
      return runner(null, node);
    }

    vm.getStructureById = function(structures, id) {
      let structure = null;
      if (structures && structures.length > 0) {
        structures.forEach(function(x) {
          if (x.id === id) {
            structure = x;
          }
        });
      }
      return structure;
    };

    vm.viewFile = function(file) {
      const params = {};
      if (file._source.href != '') {
        params.path = file._source.href + '/' + file._source.filename;
      } else {
        params.path = file._source.filename;
      }
      const showFile = $sce.trustAsResourceUrl(
        appConfig.djangoUrl + 'information-packages/' + file.information_package.id + '/files/?path=' + params.path
      );
      $window.open(showFile, '_blank');
    };

    vm.includeDescendants = false;
    vm.emailDocument = function(record) {
      return $http({
        method: 'POST',
        url: appConfig.djangoUrl + 'search/' + record._id + '/send-as-email/',
        data: {
          include_descendants: vm.includeDescendants,
        },
      }).then(function(response) {
        Notifications.add($translate.instant('EMAIL.EMAIL_SENT'), 'success');
      });
    };

    vm.gotoSearch = function() {
      $rootScope.$broadcast('CHANGE_TAB', {tab: 0});
      $state.go('home.archivalDescriptions.search');
    };

    vm.setCurrentVersion = function(node_id) {
      let node = null;
      vm.record.versions.forEach(function(version) {
        if (version._id == node_id) {
          node = version;
        }
      });
      if (node) {
        return Search.setAsCurrentVersion(node, true).then(function(response) {
          $state.reload();
        });
      }
    };

    vm.showVersion = function(node_id) {
      let node = null;
      if (vm.record.versions) {
        vm.record.versions.forEach(function(version) {
          if (version._id == node_id) {
            node = version;
          }
        });
        const versions = angular.copy(vm.record.versions);
      }
      if (node) {
        $state.go('home.archivalDescriptions.search.component', {id: node._id}, {reload: true});
      }
    };

    vm.addToStructure = function(record) {
      let parent = vm.tags.nodes.value ? vm.tags.nodes.value._id : vm.tags.structureUnits.value.id;
      Search.updateNode(
        record,
        {parent, structure_unit: vm.tags.structureUnits.value.id, structure: vm.tags.structure.value.id},
        true
      ).then(function(response) {
        $state.reload();
      });
    };

    vm.parseAgents = function(node) {
      node.agents.forEach(function(agent) {
        agent.name = AgentName.getAuthorizedName(agent.agent).full_name;
        agent.agent.auth_name = agent.name;
      });
    };

    vm.getArchiveCreator = function(node) {
      let creator = null;
      node.agents.forEach(function(agent) {
        agent.agent.name = AgentName.getAuthorizedName(agent.agent).full_name;
        if (agent.type.creator) {
          creator = agent.agent;
          creator.type = 'agent';
        }
      });
      return creator;
    };

    vm.sortNotes = function(record) {
      const obj = {
        history: [],
        remarks: [],
      };
      record.notes.forEach(function(note) {
        if (note.type.history) {
          obj.history.push(note);
        } else {
          obj.remarks.push(note);
        }
      });
      angular.extend(record, obj);
    };

    vm.exportArchive = function(node) {
      const showFile = $sce.trustAsResourceUrl(appConfig.djangoUrl + 'search/' + node._id + '/export/');
      $window.open(showFile, '_blank');
    };

    vm.archiveLabels = function(node) {
      const showFile = $sce.trustAsResourceUrl(appConfig.djangoUrl + 'search/' + node._id + '/label/');
      $window.open(showFile, '_blank');
    };

    vm.editField = function(key, value) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/edit_field_modal.html',
        scope: $scope,
        controller: 'ModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: {
            field: {
              key: key,
              value: value,
            },
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          delete vm.record[key];
          vm.record[data.key] = data.value;
          Notifications.add('Fältet: ' + data.key + ', har ändrats i: ' + vm.record.name, 'success');
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.addField = function(key, value) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/add_field_modal.html',
        scope: $scope,
        controller: 'ModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: {
            field: {
              key: '',
              value: '',
            },
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          vm.record[data.key] = data.value;
          Notifications.add('Fältet: ' + data.key + ', har lagts till i: ' + vm.record.name, 'success');
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.removeField = function(field) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/delete_field_modal.html',
        scope: $scope,
        controller: 'ModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            field: field,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          delete vm.record[field];
          Notifications.add('Fältet: ' + field + ', har tagits bort från: ' + vm.record.name, 'success');
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.viewResult = function() {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/universal_viewer_modal.html',
        scope: $scope,
        controller: 'ModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: {},
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {},
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.editNodeModal = function(node) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/edit_node_modal.html',
        controller: 'EditNodeModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: {
            node: node,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          if (vm.record._id === node._id) {
            $state.reload();
          } else {
            vm.goToNodePage(node._id, false);
          }
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    vm.addNodeModal = function(node, structure) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/add_node_modal.html',
        controller: 'AddNodeModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: {
            node: node,
            structure: structure,
            archive: vm.archive._id,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          vm.goToNodePage(data._id, false);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    vm.editArchiveModal = function(archive) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/edit_archive_modal.html',
        controller: 'ArchiveModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: {
            archive: archive,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          $state.reload();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.newVersionNodeModal = function(node) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/create_new_node_version_modal.html',
        controller: 'VersionModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: {
            node: node,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          $state.reload();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    vm.newStructureModal = function(node) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/create_new_structure_modal.html',
        controller: 'StructureModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: {
            node: node,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          $state.reload();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    vm.removeNodeModal = function(node) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_node_modal.html',
        controller: 'RemoveNodeModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: {
            node: node,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          vm.recordTreeInstance.jstree(true).delete_node(node.id);
          vm.recordTreeInstance.jstree(true).select_node(node.parent);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    vm.removeNodeFromStructureModal = function(node, structure) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_node_from_structure_modal.html',
        controller: 'RemoveNodeModalInstanceCtrl',
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
          vm.recordTreeInstance.jstree(true).delete_node(node.id);
          vm.recordTreeInstance.jstree(true).select_node(node.parent);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    vm.changeOrganizationModal = function(node) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/modals/change_node_organization.html',
        controller: 'NodeOrganizationModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: {
            node: node,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          $state.reload();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.addStructureUnitModal = function(node, structure) {
      let data = {
        node: node,
        structure: structure,
      };
      if (node._index !== 'archive') {
        data.children = getNodeById(vm.recordTreeData[0], node.id).children;
      }
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/add_structure_unit_modal.html',
        controller: 'ClassificationModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: data,
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          vm.goToNodePage(data.id, true);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.removeStructureUnitModal = function(node, structure) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_structure_unit_modal.html',
        controller: 'RemoveStructureUnitModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: {
            node: node.original,
            structure: structure,
          },
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {
          vm.recordTreeInstance.jstree(true).delete_node(node.id);
          vm.recordTreeInstance.jstree(true).select_node(node.parent);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.editStructureUnitModal = function(node, structure) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/edit_structure_unit_node_modal.html',
        controller: 'EditStructureUnitModalInstanceCtrl',
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
          $state.reload();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.addNodeRelationModal = function(node) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/add_structure_unit_relation_modal.html',
        size: 'lg',
        controller: 'StructureUnitRelationModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            node: node,
            isStructureTemplate: vm.structure.is_template,
            structure: vm.structure.id,
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $state.reload();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.editNodeRelationModal = function(relation, node) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/edit_structure_unit_relation_modal.html',
        size: 'lg',
        controller: 'StructureUnitRelationModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            relation: relation,
            node: node,
            structure: vm.structure.id,
            isStructureTemplate: vm.structure.is_template,
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $state.reload();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.removeNodeRelationModal = function(relation, node) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_structure_unit_relation_modal.html',
        size: 'lg',
        controller: 'StructureUnitRelationModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            relation: relation,
            node: node,
            structure: vm.structure.id,
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $state.reload();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.addNodeLocationModal = function(node) {
      let data = {};
      if (angular.isArray(node)) {
        data = {
          nodes: node,
        };
      } else {
        data = {
          node: node,
        };
      }
      if (node.location !== null) {
        data.location = node.location;
      }
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/tagversion_location_relation_modal.html',
        size: 'lg',
        controller: 'NodeLocationModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: data,
        },
      });
      modalInstance.result.then(
        function(data) {
          $state.reload();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.addNodeDeliveryModal = function(node) {
      let data = {};
      if (angular.isArray(node)) {
        data = {
          nodes: node,
        };
      } else {
        data = {
          node: node,
        };
      }

      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/node_delivery_relation_modal.html',
        size: 'lg',
        controller: 'NodeDeliveryModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: data,
        },
      });
      modalInstance.result.then(
        function(data) {
          $state.reload();
          vm.getTransfers(vm.transferTableState);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    vm.addNoteModal = function() {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/add_node_note_modal.html',
        controller: 'NodeNoteModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return {
              node: vm.record,
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $state.reload();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.addHistoryModal = function() {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/add_node_history_modal.html',
        controller: 'NodeNoteModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return {
              node: vm.record,
              history: true,
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $state.reload();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.editNoteModal = function(note) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/edit_node_note_modal.html',
        controller: 'NodeNoteModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return {
              node: vm.record,
              note: note,
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $state.reload();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.editHistoryModal = function(note) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/edit_node_history_modal.html',
        controller: 'NodeNoteModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return {
              node: vm.record,
              note: note,
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $state.reload();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.removeNoteModal = function(note) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_node_note_modal.html',
        controller: 'NodeNoteModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return {
              node: vm.record,
              note: note,
              allow_close: true,
              remove: true,
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $state.reload();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.removeHistoryModal = function(note) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_node_history_modal.html',
        controller: 'NodeNoteModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return {
              node: vm.record,
              note: note,
              allow_close: true,
              remove: true,
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $state.reload();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.addIdentifierModal = function() {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/add_node_identifier_modal.html',
        controller: 'NodeIdentifierModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return {
              node: vm.record,
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $state.reload();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.editIdentifierModal = function(identifier) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/edit_node_identifier_modal.html',
        controller: 'NodeIdentifierModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return {
              node: vm.record,
              identifier: identifier,
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $state.reload();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.removeIdentifierModal = function(identifier) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_node_identifier_modal.html',
        controller: 'NodeIdentifierModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return {
              node: vm.record,
              identifier: identifier,
              allow_close: true,
              remove: true,
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $state.reload();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.placeNodeInArchiveModal = function(node) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/place_node_in_archive_modal.html',
        controller: 'PlaceNodeInArchiveModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return {
              node,
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $state.reload();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
  }
}
