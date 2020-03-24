import * as angular from 'angular';

import en from '../../lang/en';
import sv from '../../lang/sv';

/* @ngInject */
const language = angular.module('essarch.language', ['pascalprecht.translate']).config([
  '$translateProvider',
  function ($translateProvider: ng.translate.ITranslateProvider) {
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
en.forEach((x) => {
  language.config(['$translateProvider', x]);
});

sv.forEach((x) => {
  language.config(['$translateProvider', x]);
});

export default language.name;
