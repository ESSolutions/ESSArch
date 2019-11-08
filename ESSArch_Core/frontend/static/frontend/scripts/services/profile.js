export const profile = ($resource, appConfig) => {
  return $resource(
    appConfig.djangoUrl + 'profiles/:id/:action/?pager=none',
    {},
    {
      get: {
        method: 'GET',
        params: {id: '@id'},
      },
      new: {
        method: 'POST',
      },
      update: {
        method: 'PUT',
        params: {id: '@id'},
      },
    }
  );
};

export const profileIp = ($resource, appConfig) => {
  return $resource(
    appConfig.djangoUrl + 'profile-ip/:id/',
    {},
    {
      query: {
        method: 'GET',
        isArray: true,
      },
      get: {
        method: 'GET',
      },
      post: {
        method: 'POST',
      },
      patch: {
        method: 'PATCH',
        params: {id: '@id'},
      },
    }
  );
};

export const profileIpData = ($resource, appConfig) => {
  return $resource(
    appConfig.djangoUrl + 'profile-ip-data/:id/:action/',
    {},
    {
      get: {
        method: 'GET',
        params: {id: '@id'},
      },
      post: {
        method: 'POST',
      },
    }
  );
};
