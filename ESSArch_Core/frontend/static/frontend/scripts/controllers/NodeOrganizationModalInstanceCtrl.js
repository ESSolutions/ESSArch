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
    $ctrl.$onInit = function () {
      if (data.node.organization) {
        $ctrl.currentOrganization = angular.copy(data.node.organization);
        $ctrl.model.organization = angular.copy(data.node.organization.id);
        $ctrl.options.organizations.push(data.node.organization);
      }
      $ctrl.buildForm();
    };

    $ctrl.getOrganizations = (search) => {
      return $http.get(appConfig.djangoUrl + 'organizations/', {params: {search: search}}).then((response) => {
        $ctrl.options.organizations = angular.copy(response.data);
        return response.data;
      });
    };

    $ctrl.buildForm = () => {
      if (data.node.type === 'agent') {
        $ctrl.fields = [
          {
            key: 'organization',
            type: 'uiselect',
            templateOptions: {
              required: true,
              label: $translate.instant('ORGANIZATION'),
              options: function () {
                return $ctrl.options.organizations;
              },
              valueProp: 'id',
              labelProp: 'name',
              placeholder: $translate.instant('ORGANIZATION'),
              appendToBody: false,
              optionsFunction: function (search) {
                return $ctrl.options.organizations;
              },
              refresh: function (search) {
                return $ctrl.getOrganizations(search).then(function () {
                  this.options = $ctrl.options.organizations;
                  return $ctrl.options.organizations;
                });
              },
            },
          },
          {
            type: 'checkbox',
            key: 'change_related_archives',
            templateOptions: {
              label: $translate.instant('CHANGE_RELATED_ARCHIVES'),
            },
            defaultValue: true,
          },
          {
            type: 'checkbox',
            key: 'change_related_ips',
            templateOptions: {
              label: $translate.instant('CHANGE_RELATED_IPS'),
            },
            defaultValue: false,
          },
        ];
      } else {
        $ctrl.fields = [
          {
            key: 'organization',
            type: 'uiselect',
            templateOptions: {
              required: true,
              label: $translate.instant('ORGANIZATION'),
              options: function () {
                return $ctrl.options.organizations;
              },
              valueProp: 'id',
              labelProp: 'name',
              placeholder: $translate.instant('ORGANIZATION'),
              appendToBody: false,
              optionsFunction: function (search) {
                return $ctrl.options.organizations;
              },
              refresh: function (search) {
                return $ctrl.getOrganizations(search).then(function () {
                  this.options = $ctrl.options.organizations;
                  return $ctrl.options.organizations;
                });
              },
            },
          },
        ];
      }
    };

    $ctrl.save = function () {
      $ctrl.saving = true;
      if (data.node.type === 'agent') {
        $ctrl.url = appConfig.djangoUrl + 'agents/' + data.node._id + '/change-organization/';
        $ctrl.data = {
          organization: $ctrl.model.organization,
          change_related_ips: $ctrl.model.change_related_ips,
          change_related_archives: $ctrl.model.change_related_archives,
        };
      } else {
        $ctrl.url = appConfig.djangoUrl + 'search/' + data.node._id + '/change-organization/';
        $ctrl.data = {
          organization: $ctrl.model.organization,
        };
      }

      $http({
        method: 'POST',
        url: $ctrl.url,
        data: $ctrl.data,
      })
        .then(function () {
          Notifications.add($translate.instant('ORGANIZATION.ORGANIZATION_CHANGED'), 'success');
          $uibModalInstance.close('changed');
          $ctrl.saving = false;
        })
        .catch(function () {
          $ctrl.saving = false;
        });
    };
    $ctrl.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
