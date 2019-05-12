export const workarea = ($resource, appConfig) => {
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
