const Step = ($resource, appConfig, Task) => {
  return $resource(
    appConfig.djangoUrl + 'steps/:id/:action/',
    {},
    {
      get: {
        method: 'GET',
        params: {id: '@id'},
      },
      query: {
        method: 'GET',
        isArray: true,
      },
      children: {
        method: 'GET',
        params: {action: 'children', id: '@id'},
        isArray: true,
        interceptor: {
          response: function(response) {
            response.resource.forEach(function(res, idx, array) {
              array[idx] = res.flow_type == 'task' ? new Task(res) : res;
            });
            response.resource.$httpHeaders = response.headers;
            return response.resource;
          },
        },
      },
      undo: {
        method: 'POST',
        params: {action: 'undo', id: '@id'},
      },
      retry: {
        method: 'POST',
        params: {action: 'retry', id: '@id'},
      },
    }
  );
};

export default Step;
