angular.module('essarch.controllers').controller('AddCtrl', function(ProfileMakerTemplate, $http, $scope, appConfig) {
  var vm = this;
  vm.options = {};

  vm.addTemplate = function(model) {
    if (model) {
      return ProfileMakerTemplate.add(model).$promise.then(function(response) {
        return response;
      });
    }
  };

  vm.addModel = {};
  vm.addFields = [
    {
      key: 'name',
      type: 'input',
      templateOptions: {
        type: 'text',
        label: 'Name',
        placeholder: '',
        required: true,
      },
    },
    {
      key: 'prefix',
      type: 'input',
      templateOptions: {
        type: 'text',
        label: 'prefix',
        placeholder: '',
        required: true,
      },
    },
    {
      key: 'root_element',
      type: 'input',
      templateOptions: {
        type: 'text',
        label: 'Root Element',
        placeholder: '',
        required: true,
      },
    },
    {
      key: 'schemaURL',
      type: 'input',
      templateOptions: {
        type: 'url',
        label: 'Schema URL',
      },
    },
  ];
  vm.originalFields = angular.copy(vm.fields);
  $scope.formData = null;
  // recieve data from element
  var unlisten = $scope.$on('fileToUpload', function(event, arg) {
    $scope.formData = arg;
  });
});
