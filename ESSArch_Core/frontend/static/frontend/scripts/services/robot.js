const robot = ($resource, appConfig) => {
  return $resource(
    appConfig.djangoUrl + 'robots/:id/:action/',
    {id: '@id'},
    {
      get: {
        method: 'GET',
        params: {id: '@id'},
      },
      queue: {
        method: 'GET',
        params: {action: 'queue', id: '@id'},
        isArray: true,
        interceptor: {
          response: function(response) {
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
            response.resource.$httpHeaders = response.headers;
            return response.resource;
          },
        },
      },
      inventory: {
        method: 'POST',
        params: {action: 'inventory', id: '@id'},
      },
    }
  );
};

export default robot;
