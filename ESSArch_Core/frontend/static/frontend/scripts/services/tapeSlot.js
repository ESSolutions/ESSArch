const tapeSlot = ($resource, appConfig) => {
  return $resource(
    appConfig.djangoUrl + 'robots/:robot_id/tape-slots/:id/:action/',
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
    }
  );
};

export default tapeSlot;
