angular.module('essarch.controllers').controller('LanguageCtrl', function(appConfig, $scope, $rootScope, $http, $cookies, $translate) {
    setUserLanguage = function(lang) {
        return $http({
            method: 'PATCH',
            url: appConfig.djangoUrl+"me/",
            data: {
                language: lang
            }
        }).then(function(response) {
            return response;
        })
    };

    getUserLanguage = function(lang) {
        return $http({
            method: 'GET',
            url: appConfig.djangoUrl+"me/",
        }).then(function(response) {
            return response.data.language;
        });
    };

    $scope.changeLanguage = function(lang) {
        setUserLanguage(lang);
        $scope.currentLanguage = lang;
        $translate.use(lang);
        moment.locale(lang);
    }

    $scope.getCurrentLanguage = function() {
        getUserLanguage().then(function(apiLang){
            $scope.changeLanguage(apiLang);
        });
    }

    $scope.getCurrentLanguage();

    $scope.loadLanguages = function() {
        $scope.availableLanguages = $translate.getAvailableLanguageKeys();
    }
    $scope.loadLanguages();
});
