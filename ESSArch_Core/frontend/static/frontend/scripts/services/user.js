angular
  .module('essarch.services')
  .factory('User', function($resource, appConfig) {
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
  })
  .factory('Me', function($resource, appConfig) {
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
  });
