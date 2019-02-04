angular.module('essarch.services').factory('Sysinfo', function($resource, appConfig) {
  return $resource(
    appConfig.djangoUrl + 'sysinfo/',
    {},
    {
      get: {
        method: 'GET',
      },
    }
  );
});
