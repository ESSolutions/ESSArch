(function() {
  'use strict';

  var app = angular.module('index', [], function config($httpProvider) {
    $httpProvider.defaults.xsrfCookieName = 'csrftoken';
    $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
  });

  app.controller('MainController', function MainCtrl($http) {
    var vm = this;
    vm.delete = function(templateName) {
      if (window.confirm('Are you sure you want to delete this template?')) {
        $http({
          method: 'POST',
          url: '/template/delete/' + templateName + '/',
        }).then(function() {
          location.reload();
        });
      }
    };
  });
})();
