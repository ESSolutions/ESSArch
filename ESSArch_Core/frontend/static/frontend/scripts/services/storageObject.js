const storageObject = ($resource, appConfig) => {
  return $resource(
    appConfig.djangoUrl + 'storage-objects/:id/:action/',
    {id: '@id'},
    {
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
    }
  );
};

export default storageObject;
