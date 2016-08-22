(function() {

    'use strict';

    angular.module('formlyApp', ['formly', 'formlyBootstrap', 'treeControl']).config(function($httpProvider) {
        $httpProvider.defaults.xsrfCookieName = 'csrftoken';
        $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
    });

})();
