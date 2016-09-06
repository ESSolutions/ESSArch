(function() {
  'use strict';

  var app = angular.module('generateForm', ['formly', 'formlyBootstrap'], function config(formlyConfigProvider, $httpProvider) {
      $httpProvider.defaults.xsrfCookieName = 'csrftoken';
      $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
    // // set templates here
    // formlyConfigProvider.setType({
    //   name: 'custom',
    //   templateUrl: 'custom.html'
    // });
  });


  app.controller('MainController', function MainCtrl(formlyVersion, $http) {
    var vm = this;
    // funcation assignment
    vm.onSubmit = function() {
        var data = vm.model;
        $http({
            method: 'POST',
            url: '/template/generate/' + templateName + '/',
            data: data
        }).then(function() {
        });
        //TODO give feedback
    };

    vm.model = {
    };
    vm.options = {
      formState: {
        awesomeIsForced: false
      }
    };

    vm.fields = [
      {
        key: 'name',
        type: 'input',
        templateOptions: {
          label: 'Name',
          placeholder: 'Name'
        }
      },
      {
        key: 'profile_type',
        type: 'select',
        templateOptions: {
          label: 'profile Type',
          options: [
            {
              name: "Transfer Project",
              value: "Transfer_Project"
            },
            {
              name: "Content Type",
              value: "Content_Type"
            },
            {
              name: "Data Selection",
              value: "Data_Selection"
            },
            {
              name: "Classification",
              value: "Classification"
            },
            {
              name: "Import",
              value: "Import"
            },
            {
              name: "Submit Description",
              value: "Submit_Description"
            },
            {
              name: "SIP",
              value: "SIP"
            },
            {
              name: "AIP",
              value: "AIP"
            },
            {
              name: "DIP",
              value: "DIP"
            },
            {
              name: "Workflow",
              value: "Workflow"
            },
            {
              name: "Preservation Description",
              value: "Preservation_Description"
            },
          ]
        }
      },
      {
        key: 'type',
        type: 'input',
        templateOptions: {
          label: 'Type',
          placeholder: 'Type'
        }
      },
      {
        key: 'status',
        type: 'input',
        templateOptions: {
          label: 'Status',
          placeholder: 'Status'
        }
      },
      {
        key: 'label',
        type: 'input',
        templateOptions: {
          label: 'Label',
          placeholder: 'Label'
        }
      },
      {
        key: 'representation_info',
        type: 'input',
        hideExpression: function($viewValue, $modelValue, scope) {
          if (scope.model.profile_type == 'SIP' || scope.model.profile_type == 'DIP' || scope.model.profile_type == 'AIP') {
            return false;
          } else {
            return true;
          }
        },
        templateOptions: {
          label: 'Representation Info',
          placeholder: 'Representation Info'
        }
      },
      {
        key: 'preservation_descriptive_info',
        type: 'input',
        hideExpression: function($viewValue, $modelValue, scope) {
          if (scope.model.profile_type == 'SIP' || scope.model.profile_type == 'DIP' || scope.model.profile_type == 'AIP') {
            return false;
          } else {
            return true;
          }
        },
        templateOptions: {
          label: 'Preservation Description Info',
          placeholder: 'Preservation Description Info'
        }
      },
      {
        key: 'supplemental',
        type: 'input',
        hideExpression: function($viewValue, $modelValue, scope) {
          if (scope.model.profile_type == 'SIP' || scope.model.profile_type == 'DIP' || scope.model.profile_type == 'AIP') {
            return false;
          } else {
            return true;
          }
        },
        templateOptions: {
          label: 'Supplemental',
          placeholder: 'Supplemental'
        }
      },
      {
        key: 'access_constraints',
        type: 'input',
        hideExpression: function($viewValue, $modelValue, scope) {
          if (scope.model.profile_type == 'SIP' || scope.model.profile_type == 'DIP' || scope.model.profile_type == 'AIP') {
            return false;
          } else {
            return true;
          }
        },
        templateOptions: {
          label: 'Access Constraints',
          placeholder: 'Access Constraints'
        }
      },
      {
        key: 'datamodel_reference',
        type: 'input',
        hideExpression: function($viewValue, $modelValue, scope) {
          if (scope.model.profile_type == 'SIP' || scope.model.profile_type == 'DIP' || scope.model.profile_type == 'AIP') {
            return false;
          } else {
            return true;
          }
        },
        templateOptions: {
          label: 'Datamodel Reference',
          placeholder: 'Datamodel Reference'
        }
      },
      {
        key: 'additional',
        type: 'input',
        hideExpression: function($viewValue, $modelValue, scope) {
          if (scope.model.profile_type == 'SIP' || scope.model.profile_type == 'DIP' || scope.model.profile_type == 'AIP') {
            return false;
          } else {
            return true;
          }
        },
        templateOptions: {
          label: 'Additional',
          placeholder: 'Additional'
        }
      },
      {
        key: 'submission_method',
        type: 'input',
        hideExpression: function($viewValue, $modelValue, scope) {
          if (scope.model.profile_type == 'SIP' || scope.model.profile_type == 'DIP' || scope.model.profile_type == 'AIP') {
            return false;
          } else {
            return true;
          }
        },
        templateOptions: {
          label: 'Submission Method',
          placeholder: 'Submission Method'
        }
      },
      {
        key: 'submission_schedule',
        type: 'input',
        hideExpression: function($viewValue, $modelValue, scope) {
          if (scope.model.profile_type == 'SIP' || scope.model.profile_type == 'DIP' || scope.model.profile_type == 'AIP') {
            return false;
          } else {
            return true;
          }
        },
        templateOptions: {
          label: 'Submission Schedule',
          placeholder: 'Submission Schedule'
        }
      },
      {
        key: 'submission_data_inventory',
        type: 'input',
        hideExpression: function($viewValue, $modelValue, scope) {
          if (scope.model.profile_type == 'SIP' || scope.model.profile_type == 'DIP' || scope.model.profile_type == 'AIP') {
            return false;
          } else {
            return true;
          }
        },
        templateOptions: {
          label: 'Submission Data Inventory',
          placeholder: 'Submission Data Inventory'
        }
      }
    ];
  });


  // app.directive('exampleDirective', function() {
  //   return {
  //     templateUrl: 'example-directive.html'
  //   };
  // });
})();
