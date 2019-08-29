const Structure = ($resource, appConfig) => {
  return $resource(
    appConfig.djangoUrl + 'structures/:id/:action/',
    {},
    {
      query: {
        method: 'GET',
        isArray: true,
        interceptor: {
          response: function(response) {
            response.resource.$httpHeaders = response.headers;
            return response.resource;
          },
        },
      },
      get: {
        method: 'GET',
        params: {id: '@id'},
      },
      new: {
        method: 'POST',
      },
      update: {
        method: 'PATCH',
        params: {id: '@id'},
      },
      remove: {
        method: 'DELETE',
        params: {id: '@id'},
      },
    }
  );
};

export default Structure;
