import get from 'lodash/get';

angular
  .module('essarch.controllers')
  .controller('SearchDetailCtrl', function(
    $scope,
    $controller,
    $stateParams,
    Search,
    $q,
    $http,
    $rootScope,
    appConfig,
    $log,
    $timeout,
    Notifications,
    $sce,
    $translate,
    $anchorScroll,
    $uibModal,
    PermPermissionStore,
    $window,
    $state,
    $interval,
    $filter,
    $transitions
  ) {
    var PAGE_SIZE = 10;

    var vm = this;
    $controller('TagsCtrl', {$scope: $scope, vm: vm});
    $scope.angular = angular;
    vm.url = appConfig.djangoUrl;
    vm.unavailable = false;
    vm.structure = null;
    vm.recordTreeData = [];

    // Record update interval
    var recordInterval;

    // Destroy intervals on state change
    $transitions.onSuccess({}, function($transition) {
      $interval.cancel(recordInterval);
    });

    vm.$onInit = function() {
      vm.loadRecordAndTree();
    };

    vm.loadRecordAndTree = function() {
      var isStructureUnit = $state.current.name == 'home.access.search.structure_unit';
      var nodeId = $stateParams.id;

      if (isStructureUnit) {
        console.log('Getting data for initial node, structure unit -', nodeId);
        var nodePromise = vm.getStructureUnit(nodeId);
      } else {
        console.log('Getting data for initial node, tag -', nodeId);
        var nodePromise = vm.getNode(nodeId);
      }

      nodePromise.then(function(data) {
        data.state = {selected: true, opened: true};
        vm.record = data;
        var startNode = data;
        var archiveId = null;

        $rootScope.$broadcast('UPDATE_TITLE', {title: vm.record.name});

        if (!data._is_structure_unit) {
          vm.currentVersion = vm.record._id;
          getVersionSelectData();

          archiveId = data.root;
        } else {
          archiveId = $stateParams.archive;
          vm.structure = vm.record.structure;
        }

        if (vm.record._id === archiveId) {
          var archive = angular.copy(vm.record);
          delete archive.parent;
          vm.archive = angular.copy(vm.record);
          vm.archiveStructures = angular.copy(archive.structures);

          if (!vm.structure && vm.record.structures.length > 0) {
            vm.structure = vm.record.structures[vm.record.structures.length - 1].id;
          }

          vm.buildTree(startNode, archive).then(function(children) {
            archive.children = children.data;
            var tree = [archive];

            vm.ignoreRecordChanges = true;
            if (!angular.equals(tree, vm.recordTreeData)) {
              angular.copy(tree, vm.recordTreeData);
            }
            vm.recordTreeConfig.version++;
          });
        } else {
          console.log('Initial node is not its own archive, getting archive:', archiveId);
          vm.getNode(archiveId).then(function(archive) {
            delete archive.parent;
            vm.archive = archive;
            vm.archiveStructures = angular.copy(archive.structures);

            if (!vm.structure && vm.record.structures.length > 0) {
              vm.structure = vm.record.structures[vm.record.structures.length - 1].id;
            }

            vm.buildTree(startNode, archive).then(function(children) {
              archive.children = children.data;
              var tree = [archive];

              vm.ignoreRecordChanges = true;
              if (!angular.equals(tree, vm.recordTreeData)) {
                angular.copy(tree, vm.recordTreeData);
              }
              vm.recordTreeConfig.version++;
            });
          });
        }
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
        node.reference_code = node._source && node._source.reference_code ? node._source.reference_code : '';
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
      return $http.get(vm.url + 'search/' + id + '/', {params: {structure: vm.structure}}).then(function(response) {
        response.data._is_structure_unit = false;
        return vm.createNode(response.data);
      });
    };

    vm.getStructureUnit = function(id) {
      return $http.get(vm.url + 'classification-structure-units/' + id + '/').then(function(response) {
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
        var deferred = $q.defer();
        deferred.resolve(null);
        return deferred.promise;
      }
    };

    vm.getChildren = function(node, archive, page) {
      var url;
      page = page || 1;

      if (node._is_structure_unit === true) {
        url = vm.url + 'classification-structure-units/' + node._id + '/children/';
      } else if (node._id === vm.archive._id) {
        return vm.getClassificationStructureChildren(vm.structure);
      } else {
        url = vm.url + 'search/' + node._id + '/children/';
      }

      console.log('Getting children to', node, 'in archive', archive._id);
      return $http
        .get(url, {params: {page_size: PAGE_SIZE, page: page, archive: archive._id, structure: vm.structure}})
        .then(function(response) {
          var data = response.data.map(function(child) {
            child._is_structure_unit = node._is_structure_unit && !node.is_unit_leaf_node;
            if (angular.isUndefined(child._id)) {
              child._id = child.id;
            }
            delete child.parent;
            return vm.createNode(child);
          });

          var count = response.headers('Count');
          console.log('Found', count, 'children to', node, 'in archive', archive._id);
          return {
            data: data,
            count: count,
          };
        });
    };

    vm.getClassificationStructureChildren = function(id) {
      var url = vm.url + 'classification-structures/' + id + '/units/';
      return $http
        .get(url, {params: {archive: vm.archive._id, has_parent: false, pager: 'none'}})
        .then(function(response) {
          var data = response.data.map(function(unit) {
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
        type: 'plus',
        _source: {},
      };
    };

    vm.buildTree = function(start, archive) {
      console.log('Building tree of', start, 'with archive', archive._id);
      return vm.getChildren(start, archive).then(function(children) {
        var existingChild =
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
            return vm.buildTree(parent, archive, vm.structure);
          } else {
            return vm.getClassificationStructureChildren(vm.structure).then(function(children) {
              var result = [];
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
        var tree = vm.recordTreeData;
        var parent = vm.recordTreeInstance.jstree(true).get_node(e.node.parent);
        var childrenNodes = tree.map(function(x) {
          return getNodeById(x, parent.original._id);
        })[0].children;
        var page = Math.ceil(childrenNodes.length / PAGE_SIZE);

        return vm.getChildren(parent.original, vm.archive, page).then(function(children) {
          var count = children.count;
          var selectedElement = null;
          var seeMore = null;

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
      }
      if (e.node.original._id !== vm.record._id) {
        vm.goToNode(e.node.id);
      }
    };

    vm.goToNode = function(id) {
      var tree = vm.recordTreeInstance.jstree(true);
      var node = tree.get_node(id);

      if (node.original._is_structure_unit != vm.record._is_structure_unit) {
        vm.goToNodePage(id, node.original._is_structure_unit);
        return;
      }

      var nodePromise = node.original._is_structure_unit
        ? vm.getStructureUnit(node.original._id)
        : vm.getNode(node.original._id);
      tree.deselect_node(vm.record.id);
      tree.select_node(node);
      nodePromise.then(function(node) {
        vm.record = node;
        vm.getChildren(vm.record, vm.archive).then(function(children) {
          vm.record.children = children.data;
        });
        $rootScope.latestRecord = node;
        if (vm.record._is_structure_unit)
          $state.go(
            'home.access.search.structure_unit',
            {id: vm.record._id, archive: vm.archive._id},
            {notify: false}
          );
        else {
          $state.go('home.access.search.' + vm.record._index, {id: vm.record._id}, {notify: false});
          getVersionSelectData();
        }
        $rootScope.$broadcast('UPDATE_TITLE', {title: vm.record.name});

        vm.currentVersion = vm.record._id;
        vm.record.breadcrumbs = getBreadcrumbs(vm.record);

        vm.getChildrenTable(vm.recordTableState);
      });
    };

    vm.goToNodePage = function(id, isStructureUnit) {
      if (isStructureUnit)
        $state.go('home.access.search.structure_unit', {id: id, archive: vm.archive._id}, {notify: true});
      else {
        $state.go('home.access.search.component', {id: id}, {notify: true});
      }
    };

    vm.getChildrenTable = function(tableState) {
      if (!angular.isUndefined(tableState)) {
        vm.recordTableState = tableState;
        var pagination = tableState.pagination;
        var start = pagination.start || 0; // This is NOT the page number, but the index of item in the list that you want to use to display the table.
        var pageSize = pagination.number || PAGE_SIZE; // Number of entries showed per page.
        var pageNumber = start / pageSize + 1;

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

    $scope.checkPermission = function(permissionName) {
      return !angular.isUndefined(PermPermissionStore.getPermissionDefinition(permissionName));
    };

    vm.existsForRecord = function(classification) {
      if (vm.record) {
        var temp = false;
        vm.record.structures.forEach(function(structure) {
          if (structure.id == classification) {
            temp = true;
          }
        });
        return temp;
      }
    };

    function getBreadcrumbs(node) {
      var tree = vm.recordTreeInstance.jstree(true);
      var start = tree.get_node(node.id);

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
        multiple: true,
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
      dnd: {
        is_draggable: function(nodes) {
          var not_draggable = nodes.some(function(node) {
            return node.original._is_structure_unit || node.original._index === 'archive';
          });
          if (not_draggable) {
            return false;
          }

          var structure = null;
          vm.archiveStructures.forEach(function(struct) {
            if (struct.id === vm.structure) {
              structure = struct;
            }
          });
          var type = nodes[0].original.type;
          return get(structure, 'specification.rules.' + type + '.movable', true);
        },
      },
      contextmenu: {
        select_node: false,
        items: function(node, callback) {
          var update = {
            label: $translate.instant('UPDATE'),
            _disabled: function() {
              return node.original._is_structure_unit;
            },
            action: function update() {
              vm.editNodeModal(node.original);
            },
          };
          var add = {
            label: $translate.instant('ADD'),
            _disabled: function() {
              return node.original._index === 'archive';
            },
            action: function() {
              vm.addNodeModal(node, vm.structure);
            },
          };
          var remove = {
            label: $translate.instant('REMOVE'),
            _disabled: function() {
              return node.original._is_structure_unit || node.original._index === 'archive';
            },
            action: function() {
              vm.removeNodeModal(node);
            },
          };
          var removeFromStructure = {
            label: $translate.instant('ACCESS.REMOVE_FROM_CLASSIFICATION_STRUCTURE'),
            _disabled: function() {
              return node.original._is_structure_unit || node.original._index === 'archive';
            },
            action: function() {
              var struct;
              vm.archiveStructures.forEach(function(item) {
                if (item.id == vm.structure) {
                  struct = item;
                }
              });
              vm.removeNodeFromStructureModal(node, struct);
            },
          };
          var newVersion = {
            label: $translate.instant('ACCESS.NEW_VERSION'),
            _disabled: function() {
              return node.original._is_structure_unit;
            },
            action: function() {
              vm.newVersionNodeModal(node);
            },
          };
          var changeOrganization = {
            label: $translate.instant('ORGANIZATION.CHANGE_ORGANIZATION'),
            _disabled: function() {
              return node.original._index !== 'archive';
            },
            action: function() {
              vm.changeOrganizationModal(vm.record);
            },
          };
          var email = {
            label: $translate.instant('EMAIL.EMAIL'),
            _disabled: function() {
              return node.original._is_structure_unit;
            },
            action: function() {
              var selected = vm.recordTreeInstance
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
          var actions = {
            update: update,
            add: add,
            email: email,
            remove: remove,
            removeFromStructure: removeFromStructure,
            newVersion: newVersion,
            changeOrganization: changeOrganization,
          };
          callback(actions);
          return actions;
        },
      },
      version: 1,
      plugins: ['types', 'contextmenu', 'dnd'],
    };

    vm.gotoNode = function(node) {
      $state.go('home.access.search.' + node._index, {id: node._id});
    };

    vm.dropNode = function(jqueryObj, data) {
      var node = data.node;
      var parentNode = vm.recordTreeInstance.jstree(true).get_node(node.parent);
      var data = {structure: vm.structure};

      if (parentNode.original._is_structure_unit) {
        data.structure_unit = parentNode.id;
      } else {
        data.parent = parentNode.id;
      }

      Search.updateNode(node.original, data, true)
        .then(function(response) {
          vm.loadRecordAndTree();
        })
        .catch(function(response) {
          Notifications.add('Could not be moved', 'error');
        });
    };

    vm.setType = function() {
      if (vm.record) {
        vm.record.breadcrumbs = getBreadcrumbs(vm.record);
      }

      vm.recordTreeInstance
        .jstree(true)
        .get_json('#', {flat: true})
        .forEach(function(item) {
          var fullItem = vm.recordTreeInstance.jstree(true).get_node(item.id);
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
        var a_date = new Date(a.create_date),
          b_date = new Date(b.create_date);
        if (a_date < b_date) return -1;
        if (a_date > b_date) return 1;
        return 0;
      });
    }

    vm.expandChildren = function(jqueryobj, e, reload) {
      var tree = vm.recordTreeData;
      if (e.node.children.length < 2 || reload) {
        var childrenNodes = tree.map(function(x) {
          return getNodeById(x, e.node.original._id);
        })[0].children;
        var page = Math.ceil(childrenNodes.length / PAGE_SIZE);

        return vm.getChildren(e.node.original, vm.archive, page).then(function(children) {
          var count = children.count;
          var selectedElement = null;
          var seeMore = null;

          if (childrenNodes[childrenNodes.length - 1].see_more) {
            seeMore = childrenNodes.pop();
            vm.recordTreeInstance.jstree(true).delete_node(e.node.id);
          } else {
            selectedElement = childrenNodes.pop();
            vm.recordTreeInstance.jstree(true).delete_node(e.node.children[e.node.children.length - 1]);
            seeMore = childrenNodes.pop();
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

    vm.getStructureById = function(structures, id) {
      var structure = null;
      structures.forEach(function(x) {
        if (x.id === id) {
          structure = x;
        }
      });
      return structure;
    };

    vm.viewFile = function(file) {
      var params = {};
      if (file.href != '') {
        params.path = file.href + '/' + file.filename;
      } else {
        params.path = file.filename;
      }
      var showFile = $sce.trustAsResourceUrl(
        appConfig.djangoUrl + 'information-packages/' + file.ip + '/files/?path=' + params.path
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
      $state.go('home.access.search');
    };

    vm.setCurrentVersion = function(node_id) {
      var node = null;
      vm.record.versions.forEach(function(version) {
        if (version._id == node_id) {
          node = version;
        }
      });
      if (node) {
        return Search.setAsCurrentVersion(node, true).then(function(response) {
          vm.loadRecordAndTree();
        });
      }
    };

    vm.showVersion = function(node_id) {
      var node = null;
      if (vm.record.versions) {
        vm.record.versions.forEach(function(version) {
          if (version._id == node_id) {
            node = version;
          }
        });
        var versions = angular.copy(vm.record.versions);
      }
      if (node) {
        vm.selectRecord(null, {node: {original: node}, action: 'select_node'});
      }
    };

    vm.addToStructure = function(record) {
      Search.updateNode(
        record,
        {parent: vm.tags.descendants.value.id, structure: vm.tags.structure.value.id},
        true
      ).then(function(response) {
        $state.reload();
      });
    };
    vm.editField = function(key, value) {
      var modalInstance = $uibModal.open({
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
      var modalInstance = $uibModal.open({
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
      var modalInstance = $uibModal.open({
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
      var modalInstance = $uibModal.open({
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
      var modalInstance = $uibModal.open({
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
          vm.loadRecordAndTree();
        },
        function() {
          vm.loadRecordAndTree();
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
          vm.loadRecordAndTree();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    vm.newVersionNodeModal = function(node) {
      var modalInstance = $uibModal.open({
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
          vm.loadRecordAndTree();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    vm.newStructureModal = function(node) {
      var modalInstance = $uibModal.open({
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
          vm.loadRecordAndTree();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    vm.removeNodeModal = function(node) {
      var modalInstance = $uibModal.open({
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
      var modalInstance = $uibModal.open({
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
      var modalInstance = $uibModal.open({
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
          vm.loadRecordAndTree();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
  });
