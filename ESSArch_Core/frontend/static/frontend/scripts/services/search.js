export default ($http, $sce, appConfig) => {
  const service = {};
  const url = appConfig.djangoUrl;
  service.query = function(filters) {
    return $http({
      method: 'GET',
      url: url + 'search/',
      params: filters,
    }).then(function(response) {
      const returnData = response.data.hits.map(function(item) {
        if (item._index.indexOf('-') >= 0) {
          item._index = item._index.split('-', 1)[0];
        }
        item._source.id = item._id;
        item._source.name = item._source.name;
        item._source.text = item._source.reference_code + ' - ' + item._source.name;
        item._source.parent = '#';
        item._source._index = item._index;
        for (const key in item.highlight) {
          item._source[key] = $sce.trustAsHtml(item.highlight[key][0]);
        }
        return item._source;
      });
      let count = response.headers('Count');
      if (count == null) {
        count = response.data.length;
      }
      return {
        numberOfPages: Math.ceil(count / filters.page_size),
        count: count,
        data: returnData,
        aggregations: response.data.aggregations,
      };
    });
  };

  service.getChildrenForTag = function(tag) {
    return $http.get(url + 'search/' + tag.id + '/children/').then(function(response) {
      const temp = response.data.map(function(item) {
        item._source.id = item._id;
        item._source.text = item._source.reference_code + ' - ' + item._source.name;
        return item._source;
      });
      return temp;
    });
  };
  service.tags = function() {};

  service.updateNode = function(node, data, refresh) {
    if (angular.isUndefined(refresh)) {
      refresh = false;
    }
    return $http({
      method: 'PATCH',
      url: url + 'search/' + node._id + '/',
      params: {
        refresh: refresh,
      },
      data: data,
    }).then(function(response) {
      return response;
    });
  };

  service.updateStructureUnit = (node, data, refresh) => {
    if (angular.isUndefined(refresh)) {
      refresh = false;
    }
    return $http({
      method: 'PATCH',
      url: url + 'structure-units/' + node._id + '/',
      params: {
        refresh: refresh,
      },
      data: data,
    }).then(response => {
      return response;
    });
  };

  service.updateNodeAndDescendants = function(node, data, deletedFields, refresh) {
    if (angular.isUndefined(refresh)) {
      refresh = false;
    }
    return $http({
      method: 'POST',
      url: url + 'search/' + node._id + '/update-descendants/',
      params: {
        refresh: refresh,
        include_self: true,
        deleted_fields: deletedFields,
      },
      data: angular.extend({structure: node.structures[0].id}, data),
    }).then(function(response) {
      return response;
    });
  };

  service.massUpdate = function(nodes, data, deletedFields, refresh) {
    if (angular.isUndefined(refresh)) {
      refresh = false;
    }
    return $http({
      method: 'POST',
      url: url + 'search/mass-update/',
      params: {
        refresh: refresh,
        deleted_fields: deletedFields,
        ids: nodes,
      },
      data: data,
    }).then(function(response) {
      return response;
    });
  };

  service.massEmail = function(nodes) {
    const ids = nodes.map(function(x) {
      return x._id;
    });
    return $http({
      method: 'POST',
      url: url + 'search/mass-email/',
      data: {
        ids: ids,
      },
    }).then(function(response) {
      return response;
    });
  };

  service.addNode = function(node) {
    return $http({
      method: 'POST',
      url: url + 'search/',
      params: {refresh: true},
      data: node,
    }).then(function(response) {
      return response;
    });
  };
  service.createNewVersion = function(node) {
    return $http({
      method: 'POST',
      url: url + 'search/' + node._id + '/new-version/',
      params: {refresh: true},
    }).then(function(response) {
      return response;
    });
  };
  service.createNewStructure = function(node, data) {
    return $http({
      method: 'POST',
      url: url + 'search/' + node._id + '/new-structure/',
      params: {refresh: true},
      data: data,
    }).then(function(response) {
      return response;
    });
  };
  service.removeNode = function(node) {
    return $http({
      method: 'DELETE',
      url: url + 'search/' + node._id + '/',
      params: {refresh: true},
    }).then(function(response) {
      return response;
    });
  };
  service.removeNodeFromStructure = function(node, structure) {
    return $http({
      method: 'POST',
      url: url + 'search/' + node._id + '/remove-from-structure/',
      params: {refresh: true},
      data: {structure: structure},
    }).then(function(response) {
      return response;
    });
  };
  service.setAsCurrentVersion = function(node, refresh) {
    return $http({
      method: 'PATCH',
      url: url + 'search/' + node._id + '/set-as-current-version/',
      params: {
        refresh: refresh,
      },
    }).then(function(response) {
      return response;
    });
  };
  return service;
};
