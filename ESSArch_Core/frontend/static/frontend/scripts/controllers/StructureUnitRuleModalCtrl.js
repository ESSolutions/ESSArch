export default class StructureUnitRuleModalCtrl {
  constructor($uibModalInstance, $http, appConfig, data, EditMode, $q, $translate, StructureUnit, Notifications) {
    const $ctrl = this;
    $ctrl.rule = {};
    $ctrl.$onInit = function () {
      $ctrl.data = data;
      if (!data.remove) {
        const typePromises = [];
        $q.all(typePromises).then(function (data) {
          $ctrl.typeOptions = [].concat.apply([], data);
          if ($ctrl.typeOptions.length > 0) {
            $ctrl.newRule = $ctrl.typeOptions.length > 0 ? $ctrl.typeOptions[0].name : null;
          }
          $ctrl.loadForm();
        });
      }
    };


    $ctrl.loadForm = function () {
      $ctrl.fields = [
        {
          key: 'movable',
          type: 'checkbox',
          templateOptions: {
            label: $translate.instant('ACCESS.CAN_BE_MOVED'),
          },
          defaultValue: false,
        },
           {
          key: 'editable',
          type: 'checkbox',
          templateOptions: {
            label: 'Kan redigeras',

          }, defaultValue: false,
        },
      ];
    };

    $ctrl.addRule = function () {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.adding = true;
      const rules = angular.copy(data.rules);
      console.log('RULES', rules)
      rules['rules'] = {movable: null, editable: null};

      rules['rules'] = {movable: $ctrl.rule.movable, editable: $ctrl.rule.editable};
      console.log("DATA", data)
      StructureUnit.update(
        {
          id: data.structure.id,
        },
        {
          specification: {
            rules: rules,
          },
        }
      ).$promise.then(function (resource) {
        $ctrl.adding = false;
        Notifications.add($translate.instant('ACCESS.RULE_ADDED'), 'success');
        EditMode.disable();
        $uibModalInstance.close(resource);
      });
    };

    $ctrl.remove = function () {
      $ctrl.removing = true;
      const rules = angular.copy(data.rules);
      angular.forEach(rules, function (value, key) {
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
      ).$promise.then(function (resource) {
        $ctrl.removing = false;
        Notifications.add($translate.instant('ACCESS.RULE_REMOVED'), 'success');
        EditMode.disable();
        $uibModalInstance.close(resource);
      });
    };

    $ctrl.cancel = function () {
      EditMode.disable();
      $uibModalInstance.dismiss('cancel');
    };
  }
}
