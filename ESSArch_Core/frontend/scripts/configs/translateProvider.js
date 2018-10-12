angular.module('essarch.configs').config(['$translateProvider', function ($translateProvider) {
    $translateProvider.useStaticFilesLoader({
        prefix: 'static/lang/',
        suffix: '.json'
    });
    $translateProvider.storageKey('essarch_language');
    $translateProvider.useCookieStorage();
    $translateProvider.useSanitizeValueStrategy("escape");
    $translateProvider.registerAvailableLanguageKeys(['en', 'sv'], {
        'en*': 'en',
        'sv*': 'sv',
        '*': 'en',
    })
    .fallbackLanguage('en')
    .determinePreferredLanguage().preferredLanguage();
}]);
