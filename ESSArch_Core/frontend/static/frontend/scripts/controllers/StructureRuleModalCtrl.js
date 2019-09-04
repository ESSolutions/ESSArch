export default class StructureRuleModalCtrl {
  constructor($uibModalInstance, $http, appConfig, data, EditMode, $q, $translate, Structure, Notifications) {
    const $ctrl = this;
    $ctrl.rule = {};
    $ctrl.$onInit = function() {
      $ctrl.data = data;
      if (!data.remove) {
        const typePromises = [];
        typePromises.push(
          $http
            .get(appConfig.djangoUrl + 'tag-version-types/', {params: {archive_type: false, pager: 'none'}})
            .then(function(response) {
              response.data.forEach(function(x) {
                x.id = x.pk;
              });
              return response.data;
            })
        );
        typePromises.push(
          $http
            .get(appConfig.djangoUrl + 'structure-unit-types/', {
              params: {structure_type: $ctrl.data.structure.structureType.id, pager: 'none'},
            })
            .then(function(response) {
              return response.data;
            })
        );
        $q.all(typePromises).then(function(data) {
          $ctrl.typeOptions = [].concat.apply([], data);
          if ($ctrl.typeOptions.length > 0) {
            $ctrl.newRule = $ctrl.typeOptions.length > 0 ? $ctrl.typeOptions[0].name : null;
          }
          $ctrl.loadForm();
        });
      }
    };

    $ctrl.loadForm = function() {
      $ctrl.fields = [
        {
          key: 'type',
          type: 'select',
          templateOptions: {
            label: $translate.instant('TYPE'),
            options: $ctrl.typeOptions,
            valueProp: 'name',
            labelProp: 'name',
            required: true,
          },
          defaultValue: $ctrl.typeOptions.length > 0 ? $ctrl.typeOptions[0].name : null,
        },
        {
          key: 'movable',
          type: 'checkbox',
          templateOptions: {
            label: $translate.instant('ACCESS.CAN_BE_MOVED'),
          },
        },
      ];
    };

    $ctrl.addRule = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.adding = true;
      const rules = angular.copy(data.rules);
      rules[$ctrl.rule.type] = {movable: $ctrl.rule.movable};
      Structure.update(
        {
          id: data.structure.id,
        },
        {
          specification: {
            rules: rules,
          },
        }
      ).$promise.then(function(resource) {
        $ctrl.adding = false;
        Notifications.add($translate.instant('ACCESS.RULE_ADDED'), 'success');
        EditMode.disable();
        $uibModalInstance.close(resource);
      });
    };

    $ctrl.remove = function() {
      $ctrl.removing = true;
      const rules = angular.copy(data.rules);
      angular.forEach(rules, function(value, key) {
        if (key == data.rule.key) {
          delete rules[key];
        }
      });
      Structure.update(
        {
          id: data.structure.id,
        },
        {
          specification: {
            rules: rules,
          },
        }
      ).$promise.then(function(resource) {
        $ctrl.removing = false;
        Notifications.add($translate.instant('ACCESS.RULE_REMOVED'), 'success');
        EditMode.disable();
        $uibModalInstance.close(resource);
      });
    };

    $ctrl.cancel = function() {
      EditMode.disable();
      $uibModalInstance.dismiss('cancel');
    };
  }
}
