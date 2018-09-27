angular.module('essarch.controllers').controller('LanguageCtrl', function($scope, $rootScope, $cookies, $cookieStore, $translate) {
    $scope.changeLanguage = function(lang) {
        $translate.use(lang);
        moment.locale(lang);
    }
    $scope.getCurrentLanguage = function() {
        var lang = $cookies.get('essarch_language');
        $scope.currentLanguage = lang;
        moment.locale(lang);
        return lang;
    }
    $scope.getCurrentLanguage();

    $scope.loadLanguages = function() {
        $scope.availableLanguages = $translate.getAvailableLanguageKeys();
    }
    $scope.loadLanguages();
});
