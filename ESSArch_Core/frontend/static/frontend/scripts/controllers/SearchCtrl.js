export default class SearchCtrl {
  constructor(
    Search,
    $scope,
    $http,
    $rootScope,
    appConfig,
    $log,
    $timeout,
    Notifications,
    $translate,
    $uibModal,
    PermPermissionStore,
    $window,
    $state,
    $httpParamSerializer,
    $stateParams,
    $transitions,
    AgentName
  ) {
    var vm = this;
    $scope.angular = angular;
    vm.url = appConfig.djangoUrl;

    vm.currentItem = null;
    vm.displayed = null;
    vm.viewResult = true;
    vm.numberOfResults = 0;
    vm.resultsPerPage = 25;
    vm.resultViewType = 'list';
    vm.options = {
      archives: [],
      agents: [],
      types: [],
    };
    vm.archiveFilter = [];
    vm.agentFilter = [];

    vm.filterObject = {
      q: '',
      type: null,
      page: 1,
      page_size: vm.resultsPerPage || 25,
      ordering: '',
    };

    vm.extensionFilter = {};

    vm.includedTypes = {
      archive: true,
      ip: true,
      component: true,
      file: true,
    };
    vm.savedSearchVisible = true;
    vm.searchList = [];

    // Change tab from outside this scope, used in search detail
    $scope.$on('CHANGE_TAB', function(event, data) {
      vm.activeTab = data.tab;
    });
    $rootScope.$on('$translateChangeSuccess', function(event, current, previous) {
      $http.get(appConfig.djangoUrl + 'search/', {params: {page_size: 0}}).then(function(response) {
        vm.loadTags(response.data.aggregations);
        vm.fileExtensions = response.data.aggregations._filter_extension.extension.buckets;
        vm.showTree = true;
      });
    });

    // When state is changed to search active tab is set to the first tab.
    // Fixing issues when backing from search detail state and no tab would be active
    $transitions.onSuccess({}, function() {
      if ($state.is('home.access.search')) {
        vm.activeTab = 0;
        vm.search(vm.tableState);
      } else {
        vm.activeTab = 1;
      }
    });

    vm.$onInit = function() {
      if (
        $state.is('home.access.search.detail') ||
        $state.is('home.access.search.information_package') ||
        $state.is('home.access.search.component') ||
        $state.is('home.access.search.archive') ||
        $state.is('home.access.search.directory') ||
        $state.is('home.access.search.document')
      ) {
        vm.activeTab = 1;
        vm.showTree = true;
      } else {
        vm.activeTab = 0;
        vm.showResults = true;
      }
      if ($stateParams.query !== null && !angular.isUndefined($stateParams.query)) {
        vm.filterObject = $stateParams.query;
      }
      $http.get(appConfig.djangoUrl + 'search/', {params: vm.filterObject}).then(function(response) {
        vm.loadTags(response.data.aggregations);
        vm.fileExtensions = response.data.aggregations._filter_extension.extension.buckets;
        vm.showTree = true;
      });
    };

    $scope.checkPermission = function(permissionName) {
      return !angular.isUndefined(PermPermissionStore.getPermissionDefinition(permissionName));
    };

    vm.goToDetailView = function() {
      if ($rootScope.latestRecord) {
        $state.go('home.access.search.' + $rootScope.latestRecord._index, {id: $rootScope.latestRecord._id});
        vm.activeTab = 1;
      }
    };

    vm.getSavedSearches = function() {
      vm.loadingSearches = true;
      $http
        .get(appConfig.djangoUrl + 'me/searches/', {pager: 'none'})
        .then(function(response) {
          vm.searchList = response.data;
          vm.loadingSearches = false;
        })
        .catch(function() {
          vm.loadingSearches = false;
        });
    };
    vm.getSavedSearches();

    vm.createArchive = function(archiveName, structureName, type, referenceCode) {
      Search.addNode({
        name: archiveName,
        structure: structureName,
        index: 'archive',
        type: type,
        reference_code: referenceCode,
      }).then(function(response) {
        vm.archiveName = null;
        vm.structureName = null;
        vm.nodeType = null;
        vm.referenceCode = null;
        Notifications.add($translate.instant('ACCESS.NEW_ARCHIVE_CREATED'), 'success');
      });
    };

    vm.changeClassificationStructure = function() {
      vm.searchSubmit(vm.filterObject.q);
      vm.openResult(vm.record);
    };
    vm.calculatePageNumber = function() {
      if (!angular.isUndefined(vm.tableState) && vm.tableState.pagination) {
        if (vm.searchResult.length == 0) {
          return (
            $translate.instant('ACCESS.SHOWING_RESULT') + ' ' + '0' + ' ' + $translate.instant('ACCESS.OF') + ' ' + '0'
          );
        }
        var pageNumber = vm.tableState.pagination.start / vm.tableState.pagination.number;
        var firstResult = pageNumber * vm.tableState.pagination.number + 1;
        var lastResult =
          vm.searchResult.length +
          (vm.tableState.pagination.start / vm.tableState.pagination.number) * vm.tableState.pagination.number;
        var total = vm.numberOfResults;
        return (
          $translate.instant('ACCESS.SHOWING_RESULT') +
          ' ' +
          firstResult +
          '-' +
          lastResult +
          ' ' +
          $translate.instant('ACCESS.OF') +
          ' ' +
          total
        );
      }
    };

    vm.clearSearch = function() {
      vm.filterObject = {
        q: '',
        type: [],
        archives: [],
        agents: [],
        page: 1,
        page_size: vm.resultsPerPage || 25,
        ordering: '',
      };
      vm.extensionFilter = {};

      vm.includedTypes = {
        archive: true,
        ip: true,
        component: true,
        file: true,
      };
      vm.searchSubmit();
    };

    vm.searchSubmit = function() {
      if (vm.tableState) {
        vm.tableState.pagination.start = 0;
      }
      $timeout(function() {
        vm.search(vm.tableState);
        vm.activeTab = 0;
      });
    };

    vm.getArchives = function(search) {
      return $http({
        url: appConfig.djangoUrl + 'tags/',
        mathod: 'GET',
        params: {page: 1, page_size: 10, index: 'archive', search: search},
      }).then(function(response) {
        vm.options.archives = response.data.map(function(x) {
          return x.current_version;
        });
        return vm.options.archives;
      });
    };

    vm.getAgents = function(search) {
      return $http({
        url: appConfig.djangoUrl + 'agents/',
        mathod: 'GET',
        params: {page: 1, page_size: 10, search: search},
      }).then(function(response) {
        response.data.forEach(function(agent) {
          AgentName.parseAgentNames(agent);
          agent.auth_name = AgentName.getAuthorizedName(agent);
        });
        vm.options.agents = response.data;
        return vm.options.agents;
      });
    };

    vm.filterNodeTypes = function(search) {
      var types = vm.options.originalTypes.filter(function(x) {
        return x.key.toLowerCase().indexOf(search.toLowerCase()) !== -1;
      });
      vm.options.types = types;
    };

    vm.formatFilters = function() {
      var filters = angular.copy(vm.filterObject);
      var includedTypes = [];
      for (var key in vm.includedTypes) {
        if (vm.includedTypes[key]) {
          includedTypes.push(key);
        }
      }
      filters.indices = includedTypes.join(',');
      var includedExtension = [];
      for (var key in vm.extensionFilter) {
        if (vm.extensionFilter[key]) {
          includedExtension.push(key);
        }
      }
      if (filters.extension == '' || filters.extension == null || filters.extension == {}) {
        delete filters.extension;
      } else {
        filters.extension = includedExtension.join(',');
      }
      if (angular.isArray(filters.archives) && filters.archives !== null) {
        filters.archives = filters.archives
          .map(function(x) {
            return x.id;
          })
          .join(',');
      }
      if (angular.isArray(filters.agents) && filters.agents !== null) {
        filters.agents = filters.agents
          .map(function(x) {
            return x.id;
          })
          .join(',');
      }
      if (angular.isArray(filters.type) && filters.type !== null) {
        filters.type = filters.type
          .map(function(x) {
            return x.key;
          })
          .join(',');
      }
      return filters;
    };

    /**
     * Pipe function for search results
     */
    vm.search = function(tableState) {
      if (tableState) {
        vm.searching = true;
        vm.tableState = tableState;
        var pagination = tableState.pagination;
        var start = pagination.start || 0; // This is NOT the page number, but the index of item in the list that you want to use to display the table.
        var number = pagination.number; // Number of entries showed per page.
        var pageNumber = isNaN(start / number) ? 1 : start / number + 1; // Prevents initial 404 response where pagenumber os NaN in request
        var ordering = tableState.sort.predicate;
        if (tableState.sort.reverse) {
          ordering = '-' + ordering;
        }
        vm.filterObject.page = pageNumber;
        vm.filterObject.page_size = number;
        vm.filterObject.ordering = ordering;
        var filters = vm.formatFilters();
        Search.query(filters).then(function(response) {
          angular.copy(response.data, vm.searchResult);
          vm.numberOfResults = response.count;
          tableState.pagination.numberOfPages = response.numberOfPages; //set the number of pages so the pagination can update
          vm.searching = false;
          vm.loadTags(response.aggregations);
          if ($state.current.name === 'home.access.search') {
            $state.go('home.access.search', {query: vm.filterObject}, {notify: false});
          }
        });
      } else {
        vm.showResults = true;
      }
    };
    vm.tags = [];

    vm.getAggregationChildren = function(aggregations, aggrType) {
      var aggregation = aggregations['_filter_' + aggrType][aggrType];
      var missing = true;
      let children = aggregation.buckets.map(function(item) {
        if (item.name) {
          item.text = item.name + ' (' + item.doc_count + ')';
          item.a_attr = {
            title: item.name,
          };
        } else {
          item.text = item.key + ' (' + item.doc_count + ')';
          item.a_attr = {
            title: item.key,
          };
        }
        item.state = {opened: true, selected: vm.filterObject[aggrType] == item.key};
        item.type = item.key;
        if (item.key == vm.filterObject[aggrType]) {
          missing = false;
        }
        item.children = [];
        return item;
      });

      if (vm.filterObject[aggrType] && missing) {
        children.push({
          key: vm.filterObject[aggrType],
          text: vm.filterObject[aggrType] + ' (0)',
          a_attr: {
            title: vm.filterObject[aggrType],
          },
          state: {opened: true, selected: true},
          type: vm.filterObject[aggrType],
          children: [],
        });
      }

      return children;
    };

    vm.loadTags = function(aggregations) {
      var typeChildren = vm.getAggregationChildren(aggregations, 'type');
      vm.options.originalTypes = aggregations._filter_type.type.buckets;
      vm.options.types = angular.copy(vm.options.originalTypes);
      var filters = [
        {
          text: $translate.instant('TYPE'),
          a_attr: {
            title: $translate.instant('TYPE'),
          },
          state: {opened: true, disabled: true},
          type: 'series',
          children: typeChildren,
          branch: 'type',
        },
      ];
      vm.recreateFilterTree(filters);
    };

    vm.getPathFromParents = function(tag) {
      if (tag.parents.length > 0) {
        vm.getTag(tag.parents[0]);
      }
    };

    vm.getTag = function(tag) {
      return $http.get(vm.url + 'search/' + tag.id + '/').then(function(response) {
        return response.data;
      });
    };

    vm.openResult = function(result, e) {
      if (!result.id && result._id) {
        result.id = result._id;
      }
      if (result._index.indexOf('-') !== -1) {
        index = result._index.split('-')[0];
      } else {
        index = result._index;
      }
      if (e.ctrlKey || e.metaKey) {
        var url = $state.href('home.access.search.' + index, {id: result.id});
        $window.open(url, '_blank');
      } else {
        $state.go('home.access.search.' + index, {id: result.id});
        vm.activeTab = 1;
      }
    };

    var newId = 1;
    vm.ignoreChanges = false;
    vm.ignoreRecordChanges = false;
    vm.newNode = {};
    vm.searchResult = [];
    vm.treeConfig = {
      core: {
        multiple: false,
        animation: 50,
        error: function(error) {
          $log.error('treeCtrl: error from js tree - ' + angular.toJson(error));
        },
        check_callback: true,
        worker: true,
        themes: {
          name: 'default',
          icons: false,
        },
      },
      version: 1,
      plugins: [],
    };

    /**
     * Recreates filter tree with given tags.
     * Version variable is updated so that the tree will detect
     * a change in the configuration object, desroy and rebuild with data from vm.tags
     */
    vm.recreateFilterTree = function(tags) {
      vm.ignoreChanges = true;
      angular.copy(tags, vm.tags);
      vm.treeConfig.version++;
    };

    vm.selectFilter = function(jqueryobj, e) {
      if (e.action == 'select_node') {
        var parent = vm.treeInstance.jstree(true).get_node(e.node.parent);
        var branch = parent.original.branch;
        if (vm.filterObject[branch] == e.node.original.key) {
          vm.treeInstance.jstree(true).deselect_node(e.node);
          vm.filterObject[branch] = null;
        } else {
          vm.filterObject[branch] = e.node.original.key;
        }
        if (vm.tableState) {
          vm.tableState.pagination.start = 0;
        }
        vm.search(vm.tableState);
      }
    };

    vm.applyModelChanges = function() {
      return !vm.ignoreChanges;
    };

    vm.getExportResultUrl = function(tableState, format) {
      if (tableState) {
        var filters = vm.formatFilters();
        if (filters.extension == '' || filters.extension == null || filters.extension == {}) {
          delete filters.extension;
        }
        var ordering = tableState.sort.predicate;
        if (tableState.sort.reverse) {
          ordering = '-' + ordering;
        }
        var params = $httpParamSerializer(
          angular.extend(
            {
              export: format,
            },
            filters
          )
        );
        return appConfig.djangoUrl + 'search/?' + params;
      } else {
        vm.showResults = true;
      }
    };

    vm.exportResultModal = function() {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'modals/export_result_modal.html',
        controller: 'ExportResultModalInstanceCtrl',
        controllerAs: '$ctrl',
        scope: $scope,
        size: 'sm',
        resolve: {
          data: function() {
            return {
              vm: vm,
            };
          },
        },
      });
      modalInstance.result
        .then(function(data) {})
        .catch(function() {
          $log.info('modal-component dismissed at: ' + new Date());
        });
    };

    vm.saveSearchModal = function() {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/save_search_modal.html',
        controller: 'SavedSearchModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'md',
        resolve: {
          data: function() {
            return {
              filters: vm.filterObject,
            };
          },
        },
      });
      modalInstance.result
        .then(function(data) {
          vm.getSavedSearches();
        })
        .catch(function() {
          $log.info('modal-component dismissed at: ' + new Date());
        });
    };

    vm.removeSearchModal = function(search) {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_search_modal.html',
        controller: 'SavedSearchModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'smd',
        resolve: {
          data: function() {
            return {
              search: search,
            };
          },
        },
      });
      modalInstance.result
        .then(function(data) {
          vm.getSavedSearches();
        })
        .catch(function() {
          $log.info('modal-component dismissed at: ' + new Date());
        });
    };
  }
}
