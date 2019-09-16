export const workarea = ($resource, appConfig, Task, Step, Event) => {
  return $resource(
    appConfig.djangoUrl + 'workareas/:id/:action/',
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
      delete: {
        method: 'DELETE',
        params: {id: '@id'},
      },
      moveToApproval: {
        method: 'POST',
        params: {action: 'receive', id: '@id'},
      },
      preserve: {
        method: 'POST',
        isArray: false,
        params: {action: 'preserve', id: '@id'},
      },
      workflow: {
        method: 'GET',
        params: {action: 'workflow', id: '@id'},
        isArray: true,
        interceptor: {
          response: function(response) {
            response.resource = response.resource.map(function(res) {
              return res.flow_type === 'task' ? new Task(res) : new Step(res);
            });
            response.resource.$httpHeaders = response.headers;
            return response.resource;
          },
        },
      },
      events: {
        method: 'GET',
        params: {action: 'events', id: '@id'},
        isArray: true,
        interceptor: {
          response: function(response) {
            response.resource.forEach(function(res, idx, array) {
              array[idx] = new Event(res);
            });
            response.resource.$httpHeaders = response.headers;
            return response.resource;
          },
        },
      },
    }
  );
};

export const workareaFiles = ($resource, appConfig) => {
  return $resource(
    appConfig.djangoUrl + 'workarea-files/:action/',
    {},
    {
      addToDip: {
        method: 'POST',
        params: {action: 'add-to-dip'},
      },
      removeFile: {
        method: 'DELETE',
        hasBody: true,
        headers: {'Content-type': 'application/json;charset=utf-8'},
      },
      addDirectory: {
        method: 'POST',
        params: {action: 'add-directory'},
      },
      mergeChunks: {
        method: 'POST',
        params: {action: 'merge-uploaded-chunks'},
      },
    }
  );
};
