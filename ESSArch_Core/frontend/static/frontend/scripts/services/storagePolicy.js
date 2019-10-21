export default ($resource, appConfig) => {
  return $resource(appConfig.djangoUrl + 'storage-policies/:id/:action/', {id: '@id'}, {});
};
