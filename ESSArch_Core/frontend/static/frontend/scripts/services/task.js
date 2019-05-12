const Task = ($resource, appConfig) => {
  return $resource(
    appConfig.djangoUrl + 'tasks/:id/:action/',
    {id: '@id'},
    {
      get: {
        method: 'GET',
        params: {id: '@id'},
        transformResponse: function(response) {
          response = angular.fromJson(response);
          response['flow_type'] = 'task';
          return response;
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
      validations: {
        method: 'GET',
        params: {action: 'validations', id: '@id'},
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

export default Task;
