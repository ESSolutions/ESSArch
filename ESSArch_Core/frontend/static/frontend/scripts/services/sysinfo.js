export default ($resource, appConfig) => {
  return $resource(
    appConfig.djangoUrl + 'sysinfo/',
    {},
    {
      get: {
        method: 'GET',
      },
    }
  );
};
