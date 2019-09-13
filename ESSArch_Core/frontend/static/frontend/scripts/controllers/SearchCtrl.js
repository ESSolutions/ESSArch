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
    const vm = this;
    $scope.angular = angular;
    vm.url = appConfig.djangoUrl;

    vm.currentItem = null;
    vm.displayed = null;
    vm.viewResult = true;
    vm.numberOfResults = 0;
    vm.resultsPerPage = 25;
    vm.resultViewType = 'list';
    vm.ignoreChanges = false;
    vm.ignoreRecordChanges = false;
    vm.newNode = {};
    vm.searchResult = [];
    vm.options = {
      archives: [],
      agents: [],
      types: [],
    };
    vm.archiveFilter = [];
    vm.agentFilter = [];

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
      if ($state.is('home.archivalDescriptions.search')) {
        vm.activeTab = 0;
      } else {
        vm.activeTab = 1;
      }
    });

    vm.$onInit = function() {
      vm.clearSearch();
      if (
        $state.is('home.archivalDescriptions.search.detail') ||
        $state.is('home.archivalDescriptions.search.structure_unit') ||
        $state.is('home.archivalDescriptions.search.information_package') ||
        $state.is('home.archivalDescriptions.search.component') ||
        $state.is('home.archivalDescriptions.search.archive') ||
        $state.is('home.archivalDescriptions.search.directory') ||
        $state.is('home.archivalDescriptions.search.document')
      ) {
        vm.activeTab = 1;
        vm.showTree = true;
      } else {
        vm.activeTab = 0;
        if ($stateParams.query !== null && !angular.isUndefined($stateParams.query)) {
          vm.filterObject = angular.copy($stateParams.query);
        }
      }
      const filters = vm.formatFilters();
      Search.query(filters).then(function(response) {
        vm.loadTags(response.aggregations);
        vm.fileExtensions = response.aggregations._filter_extension.extension.buckets;
        vm.showResults = true;
        vm.showTree = true;
      });
    };

    $scope.checkPermission = function(permissionName) {
      return !angular.isUndefined(PermPermissionStore.getPermissionDefinition(permissionName));
    };

    vm.goToDetailView = function() {
      if ($rootScope.latestRecord) {
        $state.go('home.archivalDescriptions.search.' + $rootScope.latestRecord._index, {
          id: $rootScope.latestRecord._id,
        });
        vm.activeTab = 1;
      }
    };

    vm.getSavedSearches = function() {
      vm.loadingSearches = true;
      $http
        .get(appConfig.djangoUrl + 'me/searches/', {pager: 'none'})
        .then(function(response) {
          vm.searchList = angular.copy(response.data);
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
        const pageNumber = vm.tableState.pagination.start / vm.tableState.pagination.number;
        const firstResult = pageNumber * vm.tableState.pagination.number + 1;
        const lastResult =
          vm.searchResult.length +
          (vm.tableState.pagination.start / vm.tableState.pagination.number) * vm.tableState.pagination.number;
        const total = vm.numberOfResults;
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
        type: null,
        page: 1,
        page_size: vm.resultsPerPage || 25,
        ordering: '',
        extension: {},
      };

      vm.includedTypes = {
        archive: true,
        ip: true,
        component: true,
        file: true,
      };
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
      const types = vm.options.originalTypes.filter(function(x) {
        return x.key.toLowerCase().indexOf(search.toLowerCase()) !== -1;
      });
      vm.options.types = types;
    };

    vm.formatFilters = function() {
      const filters = angular.copy(vm.filterObject);
      const includedTypes = [];
      for (let key in vm.includedTypes) {
        if (vm.includedTypes[key]) {
          includedTypes.push(key);
        }
      }
      filters.indices = includedTypes.join(',');
      const includedExtension = [];
      for (let key in filters.extension) {
        if (filters.extension[key] === true) {
          includedExtension.push(key);
        }
      }
      if (includedExtension.length <= 0) {
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
        const pagination = tableState.pagination;
        const start = pagination.start || 0; // This is NOT the page number, but the index of item in the list that you want to use to display the table.
        const number = pagination.number; // Number of entries showed per page.
        const pageNumber = isNaN(start / number) ? 1 : start / number + 1; // Prevents initial 404 response where pagenumber os NaN in request
        let ordering = tableState.sort.predicate;
        if (tableState.sort.reverse) {
          ordering = '-' + ordering;
        }
        vm.filterObject.page = pageNumber;
        vm.filterObject.page_size = number;
        vm.filterObject.ordering = ordering;
        const filters = vm.formatFilters();
        Search.query(filters).then(function(response) {
          const filterCopy = angular.copy(vm.filterObject);
          if (!angular.equals($stateParams.query, filterCopy)) {
            $state.go('home.archivalDescriptions.search', {query: filterCopy});
          }
          vm.searchResult = angular.copy(response.data);
          vm.numberOfResults = response.count;
          tableState.pagination.numberOfPages = response.numberOfPages; //set the number of pages so the pagination can update
          vm.searching = false;
          vm.loadTags(response.aggregations);
        });
      } else {
        vm.showResults = true;
      }
    };
    vm.tags = [];

    vm.getAggregationChildren = function(aggregations, aggrType) {
      const aggregation = aggregations['_filter_' + aggrType][aggrType];
      let missing = true;
      const children = aggregation.buckets.map(function(item) {
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
      const typeChildren = vm.getAggregationChildren(aggregations, 'type');
      vm.options.originalTypes = aggregations._filter_type.type.buckets;
      vm.options.types = angular.copy(vm.options.originalTypes);
      const filters = [
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
      let index;
      if (result._index.indexOf('-') !== -1) {
        index = result._index.split('-')[0];
      } else {
        index = result._index;
      }
      if (e.ctrlKey || e.metaKey) {
        const url = $state.href('home.archivalDescriptions.search.' + index, {id: result.id});
        $window.open(url, '_blank');
      } else {
        $state.go('home.archivalDescriptions.search.' + index, {id: result.id});
        vm.activeTab = 1;
      }
    };

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
        const parent = vm.treeInstance.jstree(true).get_node(e.node.parent);
        const branch = parent.original.branch;
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
        const filters = vm.formatFilters();
        if (filters.extension == '' || filters.extension == null || filters.extension == {}) {
          delete filters.extension;
        }
        let ordering = tableState.sort.predicate;
        if (tableState.sort.reverse) {
          ordering = '-' + ordering;
        }
        const params = $httpParamSerializer(
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
      const modalInstance = $uibModal.open({
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
      const modalInstance = $uibModal.open({
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
      const modalInstance = $uibModal.open({
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
