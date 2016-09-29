
(function() {

    'use strict';

    angular.module('add', ['formly', 'formlyBootstrap']).config(function($httpProvider) {
        $httpProvider.defaults.xsrfCookieName = 'csrftoken';
        $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
    }).run(function(formlyConfig) {
        formlyConfig.setType({
      name: 'upload',
      extends: 'input',
      wrapper: ['bootstrapLabel', 'bootstrapHasError'],
      link: function(scope, el, attrs) {
        el.on("change", function(changeEvent) {
          var file = changeEvent.target.files[0];
          if (file) {
            console.log('scope.id', scope.id);
            var fd = new FormData();
            // use key on backEnd
            fd.append(scope.options.key, file);
            scope.$emit('fileToUpload', fd);
            var fileProp = {};
            for (var properties in file) {
              if (!angular.isFunction(file[properties])) {
                fileProp[properties] = file[properties];
              }
            }
            scope.fc.$setViewValue(fileProp);
          } else {
            scope.fc.$setViewValue(undefined);
          }
        });
        el.on("focusout", function(focusoutEvent) {
          // dont run validation , user still opening pop up file dialog
          if ($window.document.activeElement.id === scope.id) {
            // so we set it untouched
            scope.$apply(function(scope) {
              scope.fc.$setUntouched();
            });
          } else {
            // element losing focus so we trigger validation
            scope.fc.$validate();
          }
        });

      },
      defaultOptions: {
        templateOptions: {
          type: 'file',
          required: true
        }
      }
    });
}).controller('MainController', function($http, $scope) {

        var vm = this;
        vm.onSubmit = onSubmit;
        vm.model = {};
        vm.options = {};

        function onSubmit() {
      if ($scope.formData) {
        // send the image data
        $http.post('/template/add/', $scope.formData, {
          // setting the header and CORS beyond scope of this demo, you should read more about them
        withCreadential: true,
        headers: {
          'Content-Type': undefined,
          'Access-Control-Allow-Methods': 'adjust your need',
          'Access-Control-Allow-Origin': 'adjust your need',
        },
        transformRequest: angular.identity
    }).then(function(res) {
        console.log(res.data);
    });
      }
    //   vm.options.updateInitialValue();
      alert(JSON.stringify(vm.model), null, 2);
    }

        vm.fields = [
            {
                key: 'template_name',
                type: 'input',
                templateOptions: {
                    type: 'text',
                    label: 'Tempalte Name',
                    placeholder: '',
                    required: true
                }
            },
            {
                key: 'namespace_prefix',
                type: 'input',
                templateOptions: {
                    type: 'text',
                    label: 'namespace_prefix',
                    placeholder: '',
                    required: true
                }
            },
            {
                key: 'root_element',
                type: 'input',
                templateOptions: {
                    type: 'text',
                    label: 'Root Element',
                    placeholder: '',
                    required: true
                }
            },
            {
                key: 'file',
                type: 'upload',
                templateOptions: {
                    // type: 'file',
                    label: 'Root Element',
                    // placeholder: '',
                    // required: true
                }
            },
            {
                key: 'file2',
                type: 'upload',
                templateOptions: {
                    // type: 'upload',
                    label: 'Root Element',
                    // placeholder: '',
                    // required: true
                }
            },
        ];
        vm.originalFields = angular.copy(vm.fields);
    $scope.formData = null;
    // recieve data from element
    var unlisten = $scope.$on('fileToUpload', function(event, arg) {
      $scope.formData = arg;
    });

    });

})();
