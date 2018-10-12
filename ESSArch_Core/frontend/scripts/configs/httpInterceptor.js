angular.module('essarch').config(['$httpProvider', '$windowProvider', function($httpProvider, $windowProvider) {
    var $window = $windowProvider.$get();
    $httpProvider.defaults.xsrfCookieName = 'csrftoken';
    $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
    $httpProvider.interceptors.push(['$q', '$location', '$rootScope', function ($q, $location, $rootScope) {
        return {
            'response': function(response) {
                if($rootScope.disconnected) {
                    $rootScope.disconnected = false;
                    $rootScope.$broadcast("reconnected", {detail: "Connection has been restored"});
                }
                return response;
            },
            'responseError': function(response) {
                if(response.status == 500) {
                    var msg = "Internal server error";
                    if(response.data.detail) {
                        msg = response.data.detail;
                    }
                    $rootScope.$broadcast('add_notification', { message: msg, level: "error", time: null});
                }
                if(response.status === 503) {
                    var msg = "Request failed, try again";
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
                    var msg = "You do not have permission to perform this action";
                    if(response.data.detail) {
                        msg = response.data.detail;
                    }
                    $rootScope.$broadcast('add_notification', { message: msg, level: "error", time: null});
                }
                if(response.status <= 0) {
                    $rootScope.$broadcast("disconnected", {detail: "Lost connection to server"});
                }
                return $q.reject(response);
            }
        };
    }]);
}])
