const storageMedium = ($resource, appConfig) => {
  return $resource(
    appConfig.djangoUrl + 'storage-mediums/:id/:action/',
    {id: '@id'},
    {
      get: {
        method: 'GET',
        params: {id: '@id'},
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
      objects: {
        method: 'GET',
        params: {action: 'storage-objects', id: '@id'},
        isArray: true,
        interceptor: {
          response: function(response) {
            response.resource.$httpHeaders = response.headers;
            return response.resource;
          },
        },
      },
      mount: {
        method: 'POST',
        params: {action: 'mount', id: '@id'},
      },
      unmount: {
        method: 'POST',
        params: {action: 'unmount', id: '@id'},
      },
    }
  );
};

export default storageMedium;
