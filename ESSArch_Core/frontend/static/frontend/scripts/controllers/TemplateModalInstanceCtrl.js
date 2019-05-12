angular
  .module('essarch.controllers')
  .controller('TemplateModalInstanceCtrl', function(ProfileMakerTemplate, $uibModalInstance, djangoAuth, data) {
    var $ctrl = this;
    $ctrl.angular = angular;
    $ctrl.template = data.template;
    if (data.template && data.template.structure) {
      $ctrl.oldStructure = angular.copy(data.template.structure);
    }
    $ctrl.allAttributes = data.allAttributes;
    $ctrl.save = data.save;
    $ctrl.model = data.model;
    $ctrl.fields = data.fields;
    $ctrl.treeOptions = {
      nodeChildren: 'children',
      dirSelectable: true,
      injectClasses: {
        ul: 'a1',
        li: 'a2',
        liSelected: 'a7',
        iExpanded: 'a3',
        iCollapsed: 'a4',
        iLeaf: 'a5',
        label: 'a6',
        labelSelected: 'a8',
      },
    };
    $ctrl.generateTemplate = function() {
      $ctrl.data = $ctrl.model;
      data.generate($ctrl.data).then(function(response) {
        $uibModalInstance.close(response);
      });
    };
    $ctrl.saveStructure = function(structure) {
      $ctrl.data = structure;
      ProfileMakerTemplate.update({templateName: $ctrl.template.name}, {structure: structure}).$promise.then(function(
        resource
      ) {
        $uibModalInstance.close(resource);
      });
    };
    $ctrl.addTemplate = function() {
      $ctrl.data = $ctrl.model;
      data.add($ctrl.data).then(function(response) {
        $uibModalInstance.close(response);
      });
    };
    $ctrl.addExtension = function() {
      $ctrl.data = $ctrl.model;
      data.add($ctrl.data).then(function(data) {
        $ctrl.template.extensions.push(data.id);
        ProfileMakerTemplate.update(
          {templateName: $ctrl.template.name},
          {
            extensions: $ctrl.template.extensions,
          }
        ).$promise.then(function(resource) {
          $uibModalInstance.close(resource);
        });
      });
    };
    $ctrl.saveAttribute = function() {
      $ctrl.data = $ctrl.model;
      data.save($ctrl.data).then(function(response) {
        $uibModalInstance.close(response);
      });
    };
    $ctrl.addAttribute = function(nodeData, parent) {
      data.add(nodeData, parent).then(function(response) {
        $uibModalInstance.close(response);
      });
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  });
