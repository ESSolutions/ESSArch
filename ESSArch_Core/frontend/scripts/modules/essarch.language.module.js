angular.module('essarch.language', ['pascalprecht.translate']).config([
  '$translateProvider',
  function($translateProvider) {
    $translateProvider.storageKey('essarch_language');
    $translateProvider.useCookieStorage();
    $translateProvider.useSanitizeValueStrategy('escape');
    $translateProvider
      .registerAvailableLanguageKeys(['en', 'sv'], {
        'en*': 'en',
        'sv*': 'sv',
        '*': 'en',
      })
      .fallbackLanguage('en')
      .determinePreferredLanguage()
      .preferredLanguage();
  },
]);
