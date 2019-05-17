export const user = ($resource, appConfig) => {
  return $resource(
    appConfig.djangoUrl + 'users/:id/:action/',
    {id: '@id'},
    {
      get: {
        method: 'GET',
        params: {id: '@id'},
      },
      changeIpViewType: {
        method: 'PATCH',
        params: {id: '@id'},
      },
    }
  );
};

export const me = ($resource, appConfig) => {
  return $resource(
    appConfig.djangoUrl + 'me/:action/',
    {},
    {
      get: {
        method: 'GET',
      },
      update: {
        method: 'PATCH',
      },
    }
  );
};
