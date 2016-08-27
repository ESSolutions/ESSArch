(function() {

    'use strict';

    angular.module('formlyApp', ['formly', 'formlyBootstrap']).config(function($httpProvider) {
        $httpProvider.defaults.xsrfCookieName = 'csrftoken';
        $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
    });

})();
