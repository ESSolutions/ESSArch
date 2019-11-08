export default class NodeOrganizationModalInstanceCtrl {
  constructor($translate, $uibModalInstance, appConfig, $http, data, Notifications, Organization) {
    const $ctrl = this;
    $ctrl.node = data.node;
    $ctrl.saving = false;
    $ctrl.options = {
      organizations: [],
    };
    $ctrl.model = {};
    $ctrl.fields = [];
    $ctrl.$onInit = function() {
      if (data.node) {
        $ctrl.currentOrganization = angular.copy(data.node.organization);
        $ctrl.model.organization = angular.copy(data.node.organization.id);
        $ctrl.options.organizations.push(data.node.organization);
      }
      $ctrl.buildForm();
    };

    $ctrl.getOrganizations = search => {
      return $http.get(appConfig.djangoUrl + 'organizations/', {params: {search: search}}).then(response => {
        $ctrl.options.organizations = angular.copy(response.data);
        return response.data;
      });
    };

    $ctrl.buildForm = () => {
      $ctrl.fields = [
        {
          key: 'organization',
          type: 'uiselect',
          templateOptions: {
            required: true,
            label: $translate.instant('ORGANIZATION'),
            options: function() {
              return $ctrl.options.organizations;
            },
            valueProp: 'id',
            labelProp: 'name',
            placeholder: $translate.instant('ORGANIZATION'),
            appendToBody: false,
            optionsFunction: function(search) {
              return $ctrl.options.organizations;
            },
            refresh: function(search) {
              return $ctrl.getOrganizations(search).then(function() {
                this.options = $ctrl.options.organizations;
                return $ctrl.options.organizations;
              });
            },
          },
        },
      ];
    };

    $ctrl.save = function() {
      $ctrl.saving = true;
      $http({
        method: 'POST',
        url: appConfig.djangoUrl + 'search/' + data.node._id + '/change-organization/',
        data: {
          organization: $ctrl.model.organization,
        },
      })
        .then(function() {
          Notifications.add($translate.instant('ORGANIZATION.ORGANIZATION_CHANGED'), 'success');
          $uibModalInstance.close('changed');
          $ctrl.saving = false;
        })
        .catch(function() {
          $ctrl.saving = false;
        });
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
