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
        }).then(function(res) {
          console.log(res.data)
        });
        //TODO give feedback
    };

    vm.model = {
      name:"",
      profile_type:"",
      type:"",
      status:"",
      label:"",
      representation_info:"",
      preservation_descriptive_info:"",
      supplemental:"",
      access_constraints:"",
      datamodel_reference:"",
      additional:"",
      submission_method:"",
      submission_schedule:"",
      submission_data_inventory:""
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
              value: "transfer_project"
            },
            {
              name: "Content Type",
              value: "content_type"
            },
            {
              name: "Data Selection",
              value: "data_selection"
            },
            {
              name: "Classification",
              value: "classification"
            },
            {
              name: "Import",
              value: "import"
            },
            {
              name: "Submit Description",
              value: "submit_description"
            },
            {
              name: "SIP",
              value: "sip"
            },
            {
              name: "AIP",
              value: "aip"
            },
            {
              name: "DIP",
              value: "dip"
            },
            {
              name: "Workflow",
              value: "workflow"
            },
            {
              name: "Preservation Description",
              value: "preservation_description"
            },
            {
              name: "Event",
              value: "event"
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
