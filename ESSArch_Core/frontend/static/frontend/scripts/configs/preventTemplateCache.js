const preventTemplateCache = [
  '$provide',
  '$httpProvider',
  '$windowProvider',
  function ($provide, $httpProvider, $windowProvider) {
    $provide.factory('preventTemplateCache', [
      '$q',
      '$location',
      '$rootScope',
      '$injector',
      function ($q, $location, $rootScope, $injector) {
        return {
          request: function (config) {
            if (config.url.indexOf('views') !== -1) {
              config.url = config.url + '?t=' + COMMITHASH;
            }
            return config;
          },
        };
      },
    ]);
    $httpProvider.interceptors.push('preventTemplateCache');
  },
];

export default preventTemplateCache;
