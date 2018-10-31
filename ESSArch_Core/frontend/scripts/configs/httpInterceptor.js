angular.module('essarch').config(['$provide', '$httpProvider', '$windowProvider', function($provide, $httpProvider, $windowProvider) {
    var $window = $windowProvider.$get();
    $httpProvider.defaults.xsrfCookieName = 'csrftoken';
    $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
    $provide.factory('httpInterceptor', ['$q', '$location', '$rootScope', '$injector', function ($q, $location, $rootScope, $injector) {
        return {
            'response': function(response) {
                var translation = $injector.get('$translate');
                if($rootScope.disconnected) {
                    $rootScope.disconnected = false;
                    $rootScope.$broadcast("reconnected", {detail: translation.instant("CONNECTION_RESTORED")});
                }
                return response;
            },
            'responseError': function(response) {
                var translation = $injector.get('$translate');
                if(response.status == 500) {
                    var msg = translation.instant("ERROR_500");
                    if(response.data.detail) {
                        msg = response.data.detail;
                    }
                    $rootScope.$broadcast('add_notification', { message: msg, level: "error", time: null});
                }
                if(response.status === 503) {
                    var msg = translation.instant("ERROR_503");
                    if(response.data.detail) {
                        msg = response.data.detail;
                    }
                    $rootScope.$broadcast('add_notification', { message: msg, level: "error", time: null});
                }
                if(response.status === 401 && !response.config.noAuth) {
                    if ($location.path() != '/login' && $location.path() != ''){
                        $window.location.assign('/');
                    }
                }
                if(response.status === 403) {
                    var msg = translation.instant("ERROR_403");
                    if(response.data.detail) {
                        msg = response.data.detail;
                    }
                    $rootScope.$broadcast('add_notification', { message: msg, level: "error", time: null});
                }
                if(response.status <= 0) {
                    $rootScope.$broadcast("disconnected", {detail: translation.instant("CONNECTION_LOST")});
                }
                return $q.reject(response);
            }
        };
    }]);
    $httpProvider.interceptors.push('httpInterceptor');
}])
