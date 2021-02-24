export default ($resource, appConfig) => {
  return $resource(
    appConfig.djangoUrl + 'storage-policies/:id/:action/',
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
