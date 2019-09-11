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
    structureUnits: {
      options: [],
      value: null,
      previous: null,
    },
    nodes: {
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
      structureUnits: {
        options: [],
        value: null,
        previous: null,
      },
      nodes: {
        options: [],
        value: null,
        previous: null,
      },
    };
  };

  $scope.getArchives = function(search) {
    $scope.archivesLoading = true;
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
      $scope.archivesLoading = false;
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

  $scope.getStructureUnits = function(archive, structure, search) {
    $scope.structureUnitsLoading = true;
    return $http({
      method: 'GET',
      url: appConfig.djangoUrl + 'structure-units/',
      params: {structure, archive, template: false, search: search ? search : null},
    }).then(function(response) {
      $scope.structureUnitsLoading = false;
      vm.tags.structureUnits.options = angular.copy(response.data);
      return response.data;
    });
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
      $scope.getStructureUnits(vm.tags.archive.value.parent_id, vm.tags.structure.value.id);
      vm.tags.structureUnits.value = null;
      vm.tags.structure.previous = item.id;
    }
  };
};
