const tag = (IP, $resource, appConfig) => {
  var Tag = $resource(
    appConfig.djangoUrl + 'tags/:id/:action/',
    {id: '@id'},
    {
      get: {
        method: 'GET',
        params: {id: '@id'},
        interceptor: {
          response: function(response) {
            response.resource.children.forEach(function(child, idx, array) {
              array[idx] = new Tag(child);
            });
            response.resource.$httpHeaders = response.headers;
            return response.resource;
          },
        },
      },
      query: {
        method: 'GET',
        params: {id: '@id'},
        isArray: true,
        interceptor: {
          response: function(response) {
            response.resource.forEach(function(res) {
              res.children.forEach(function(child, idx, array) {
                array[idx] = new Tag(child);
              });
            });
            response.resource.$httpHeaders = response.headers;
            return response.resource;
          },
        },
      },
      update: {
        method: 'PATCH',
        params: {id: '@id'},
      },
      information_packages: {
        method: 'GET',
        params: {id: '@id', action: 'information-packages'},
        isArray: true,
        interceptor: {
          response: function(response) {
            response.data.forEach(function(child, idx, array) {
              array[idx] = new IP(child);
            });
            response.resource.concat(response.data);
            response.resource.$httpHeaders = response.headers;
            return response.resource;
          },
        },
      },
    }
  );
  return Tag;
};

export default tag;
