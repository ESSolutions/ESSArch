import moment from 'moment';

import 'moment/locale/sv.js';

const LanguageCtrl = (appConfig, $scope, $http, $translate) => {
  const setUserLanguage = lang => {
    return $http({
      method: 'PATCH',
      url: appConfig.djangoUrl + 'me/',
      data: {
        language: lang,
      },
    }).then(function(response) {
      return response;
    });
  };

  const getUserLanguage = lang => {
    return $http({
      method: 'GET',
      url: appConfig.djangoUrl + 'me/',
    }).then(function(response) {
      return response.data.language;
    });
  };

  $scope.changeLanguage = function(lang) {
    setUserLanguage(lang);
    $scope.currentLanguage = lang;
    $translate.use(lang);
    moment.locale(lang);
  };

  $scope.getCurrentLanguage = function() {
    getUserLanguage().then(function(apiLang) {
      $scope.changeLanguage(apiLang);
    });
  };

  $scope.getCurrentLanguage();

  $scope.loadLanguages = function() {
    $scope.availableLanguages = $translate.getAvailableLanguageKeys();
  };
  $scope.loadLanguages();
};

export default LanguageCtrl;
