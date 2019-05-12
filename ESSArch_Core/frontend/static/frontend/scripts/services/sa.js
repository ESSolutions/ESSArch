const sa = ($resource, appConfig) => {
  return $resource(
    appConfig.djangoUrl + 'submission-agreements/:id/:action/',
    {},
    {
      get: {
        method: 'GET',
        params: {id: '@id'},
      },
      includeType: {
        method: 'POST',
        params: {action: 'include-type', id: '@id'},
      },
      excludeType: {
        method: 'POST',
        params: {action: 'exclude-type', id: '@id'},
      },
      save: {
        method: 'POST',
      },
      new: {
        method: 'POST',
      },
      update: {
        method: 'PUT',
        params: {id: '@id'},
      },
      publish: {
        method: 'POST',
        params: {action: 'publish', id: '@id'},
      },
      lock: {
        method: 'POST',
        params: {action: 'lock', id: '@id'},
      },
    }
  );
};

export default sa;
