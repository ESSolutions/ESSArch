const order = ($resource, appConfig) => {
  return $resource(
    appConfig.djangoUrl + 'orders/:id/:action/',
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
    }
  );
};

export default order;
