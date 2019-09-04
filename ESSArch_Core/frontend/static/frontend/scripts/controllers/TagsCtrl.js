export default ($scope, vm, $http, appConfig) => {
  vm.tags = {
    archive: {
      options: [],
      value: null,
      previous: null,
    },
    structure: {
      options: [],
      value: null,
      previous: null,
    },
    descendants: {
      options: [],
      value: null,
      previous: null,
    },
  };
  vm.resetForm = function() {
    vm.tags = {
      archive: {
        options: [],
        value: null,
        previous: null,
      },
      structure: {
        options: [],
        value: null,
        previous: null,
      },
      descendants: {
        options: [],
        value: null,
        previous: null,
      },
    };
  };

  $scope.getArchives = function(search) {
    return $http({
      method: 'GET',
      url: appConfig.djangoUrl + 'tags/',
      params: {index: 'archive', search: search ? search : null},
    }).then(function(response) {
      const mapped = response.data.map(function(item) {
        const obj = item.current_version;
        obj.parent_id = item.id;
        obj.structures = item.structures;
        return obj;
      });
      vm.tags.archive.options = mapped;
      return mapped;
    });
  };

  // Functions for selects when placing unplaced node
  $scope.getStructures = function(archive) {
    $scope.structuresLoading = true;
    const mapped = archive.structures.map(function(item) {
      const obj = item.structure;
      obj.parent_id = item.id;
      return obj;
    });
    $scope.structuresLoading = false;
    vm.tags.structure.options = mapped;
  };

  $scope.getTagDescendants = function(id1, id2, search) {
    $scope.descendantsLoading = true;
    return $http({
      method: 'GET',
      url: appConfig.djangoUrl + 'tags/' + id1 + '/descendants/',
      params: {structure: id2, search: search ? search : null, index: 'component'},
    }).then(function(response) {
      const mapped = response.data.map(function(item) {
        const obj = item.current_version;
        obj.parent_id = item.id;
        obj.structures = item.structures;
        return obj;
      });
      $scope.descendantsLoading = false;
      vm.tags.descendants.options = mapped;
      return mapped;
    });
  };

  $scope.getDescendantId = function() {
    if (vm.tags.structure.value && vm.tags.descendants.value) {
      var id = null;
      vm.tags.descendants.value.structures.forEach(function(item) {
        if (item.structure.id == vm.tags.structure.value.id) {
          id = item.id;
        }
      });
      return id;
    } else if (vm.tags.archive.value && vm.tags.structure.value) {
      var id = null;
      vm.tags.archive.value.structures.forEach(function(item) {
        if (item.structure.id == vm.tags.structure.value.id) {
          id = item.id;
        }
      });
      return id;
    } else {
      return null;
    }
  };

  $scope.archiveChanged = function(item) {
    if ((vm.tags.archive.previous = null || item.id != vm.tags.archive.previous)) {
      $scope.getStructures(vm.tags.archive.value);
      vm.tags.structure.value = null;
      vm.tags.archive.previous = item.id;
    }
  };
  $scope.structureChanged = function(item) {
    if (vm.tags.structure.previous == null || item.id != vm.tags.structure.previous) {
      $scope.getTagDescendants(vm.tags.archive.value.parent_id, vm.tags.structure.value.id);
      vm.tags.descendants.value = null;
      vm.tags.structure.previous = item.id;
    }
  };
};
