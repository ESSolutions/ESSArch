angular.module('essarch.directives').directive('fileread', [
  function() {
    return {
      scope: {
        fileread: '=',
      },
      link: function(scope, element, attributes) {
        element.bind('change', function(changeEvent) {
          var reader = new FileReader();
          reader.onload = function(loadEvent) {
            scope.$apply(function() {
              scope.fileread = loadEvent.target.result;
              element[0].value = '';
            });
          };
          reader.readAsText(changeEvent.target.files[0]);
        });
      },
    };
  },
]);
