const tapeDrive = ($resource, appConfig) => {
  return $resource(
    appConfig.djangoUrl + 'robots/:robot_id/tape-drives/:id/:action/',
    {robot_id: '@robot_id', id: '@id'},
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
          response: function (response) {
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

export default tapeDrive;
