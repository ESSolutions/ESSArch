export default class OrganizationModalInstanceCtrl {
  constructor($translate, $uibModalInstance, appConfig, $http, data, Notifications, Organization) {
    const $ctrl = this;
    $ctrl.itemType = data.itemType;
    $ctrl.item = data.item;
    $ctrl.saving = false;
    $ctrl.options = {
      organizations: [],
    };
    $ctrl.model = {};
    $ctrl.fields = [];
    $ctrl.$onInit = function () {
      if (data.itemType === 'archive' && data.item && data.item.current_version.organization) {
        $ctrl.currentOrganization = angular.copy(data.item.current_version.organization);
        $ctrl.model.organization = angular.copy(data.item.current_version.organization.id);
        $ctrl.options.organizations.push(data.item.current_version.organization);
      } else if (data.item && data.item.organization) {
        $ctrl.currentOrganization = angular.copy(data.item.organization);
        $ctrl.model.organization = angular.copy(data.item.organization.id);
        $ctrl.options.organizations.push(data.item.organization);
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

      if (data.itemType === 'agent') {
        $ctrl.fields.push({
          type: 'checkbox',
          key: 'force',
          templateOptions: {
            label: $translate.instant('FORCE'),
          },
        });
        $ctrl.fields.push({
          type: 'checkbox',
          key: 'change_related_Archives',
          defaultValue: true,
          templateOptions: {
            label: $translate.instant('CHANGE_RELATED_ARCHIVES'),
          },
        });
        $ctrl.fields.push({
          type: 'checkbox',
          key: 'change_related_Archives_force',
          templateOptions: {
            label: $translate.instant('CHANGE_RELATED_ARCHIVES_FORCE'),
          },
        });
        // $ctrl.fields.push({
        //   type: 'checkbox',
        //   key: 'change_related_StructureUnits',
        //   templateOptions: {
        //     label: $translate.instant('CHANGE_RELATED_STRUCTUREUNITS'),
        //   },
        // });
        // $ctrl.fields.push({
        //   type: 'checkbox',
        //   key: 'change_related_StructureUnits_force',
        //   templateOptions: {
        //     label: $translate.instant('CHANGE_RELATED_STRUCTUREUNITS_FORCE'),
        //   },
        // });
        $ctrl.fields.push({
          type: 'checkbox',
          key: 'change_related_Nodes',
          defaultValue: true,
          templateOptions: {
            label: $translate.instant('CHANGE_RELATED_NODES'),
          },
        });
        $ctrl.fields.push({
          type: 'checkbox',
          key: 'change_related_Nodes_force',
          templateOptions: {
            label: $translate.instant('CHANGE_RELATED_NODES_FORCE'),
          },
        });
        $ctrl.fields.push({
          type: 'checkbox',
          key: 'change_related_IPs',
          defaultValue: true,
          templateOptions: {
            label: $translate.instant('CHANGE_RELATED_IPS'),
          },
        });
        $ctrl.fields.push({
          type: 'checkbox',
          key: 'change_related_IPs_force',
          templateOptions: {
            label: $translate.instant('CHANGE_RELATED_IPS_FORCE'),
          },
        });
        $ctrl.fields.push({
          type: 'checkbox',
          key: 'change_related_AIDs',
          defaultValue: true,
          templateOptions: {
            label: $translate.instant('CHANGE_RELATED_AIDS'),
          },
        });
        $ctrl.fields.push({
          type: 'checkbox',
          key: 'change_related_AIDs_force',
          templateOptions: {
            label: $translate.instant('CHANGE_RELATED_AIDS_FORCE'),
          },
        });
      } else if (data.itemType === 'archive') {
        $ctrl.fields.push({
          type: 'checkbox',
          key: 'force',
          templateOptions: {
            label: $translate.instant('FORCE'),
          },
        });
        // $ctrl.fields.push({
        //   type: 'checkbox',
        //   key: 'change_related_StructureUnits',
        //   templateOptions: {
        //     label: $translate.instant('CHANGE_RELATED_STRUCTUREUNITS'),
        //   },
        // });
        // $ctrl.fields.push({
        //   type: 'checkbox',
        //   key: 'change_related_StructureUnits_force',
        //   templateOptions: {
        //     label: $translate.instant('CHANGE_RELATED_STRUCTUREUNITS_FORCE'),
        //   },
        // });
        $ctrl.fields.push({
          type: 'checkbox',
          key: 'change_related_Nodes',
          defaultValue: true,
          templateOptions: {
            label: $translate.instant('CHANGE_RELATED_NODES'),
          },
        });
        $ctrl.fields.push({
          type: 'checkbox',
          key: 'change_related_Nodes_force',
          templateOptions: {
            label: $translate.instant('CHANGE_RELATED_NODES_FORCE'),
          },
        });
        $ctrl.fields.push({
          type: 'checkbox',
          key: 'change_related_IPs',
          defaultValue: true,
          templateOptions: {
            label: $translate.instant('CHANGE_RELATED_IPS'),
          },
        });
        $ctrl.fields.push({
          type: 'checkbox',
          key: 'change_related_IPs_force',
          templateOptions: {
            label: $translate.instant('CHANGE_RELATED_IPS_FORCE'),
          },
        });
        $ctrl.fields.push({
          type: 'checkbox',
          key: 'change_related_AIDs',
          defaultValue: true,
          templateOptions: {
            label: $translate.instant('CHANGE_RELATED_AIDS'),
          },
        });
        $ctrl.fields.push({
          type: 'checkbox',
          key: 'change_related_AIDs_force',
          templateOptions: {
            label: $translate.instant('CHANGE_RELATED_AIDS_FORCE'),
          },
        });
      }
    };

    $ctrl.save = function () {
      $ctrl.saving = true;
      $ctrl.data = {
        organization: $ctrl.model.organization,
      };
      if (data.itemType === 'agent') {
        $ctrl.url = appConfig.djangoUrl + 'agents/' + data.item.id + '/change-organization/';
        $ctrl.data['force'] = $ctrl.model.force;
        $ctrl.data['change_related_Archives'] = $ctrl.model.change_related_Archives;
        $ctrl.data['change_related_Archives_force'] = $ctrl.model.change_related_Archives_force;
        $ctrl.data['change_related_StructureUnits'] = $ctrl.model.change_related_StructureUnits;
        $ctrl.data['change_related_StructureUnits_force'] = $ctrl.model.change_related_StructureUnits_force;
        $ctrl.data['change_related_Nodes'] = $ctrl.model.change_related_Nodes;
        $ctrl.data['change_related_Nodes_force'] = $ctrl.model.change_related_Nodes_force;
        $ctrl.data['change_related_IPs'] = $ctrl.model.change_related_IPs;
        $ctrl.data['change_related_IPs_force'] = $ctrl.model.change_related_IPs_force;
        $ctrl.data['change_related_AIDs'] = $ctrl.model.change_related_AIDs;
        $ctrl.data['change_related_AIDs_force'] = $ctrl.model.change_related_AIDs_force;
      } else if (data.itemType === 'ip') {
        $ctrl.url = appConfig.djangoUrl + 'information-packages/' + data.item.id + '/change-organization/';
      } else if (data.itemType === 'archive') {
        $ctrl.url = appConfig.djangoUrl + 'search/' + data.item.current_version.id + '/change-organization/';
        $ctrl.data['force'] = $ctrl.model.force;
        $ctrl.data['change_related_StructureUnits'] = $ctrl.model.change_related_StructureUnits;
        $ctrl.data['change_related_StructureUnits_force'] = $ctrl.model.change_related_StructureUnits_force;
        $ctrl.data['change_related_Nodes'] = $ctrl.model.change_related_Nodes;
        $ctrl.data['change_related_Nodes_force'] = $ctrl.model.change_related_Nodes_force;
        $ctrl.data['change_related_IPs'] = $ctrl.model.change_related_IPs;
        $ctrl.data['change_related_IPs_force'] = $ctrl.model.change_related_IPs_force;
        $ctrl.data['change_related_AIDs'] = $ctrl.model.change_related_AIDs;
        $ctrl.data['change_related_AIDs_force'] = $ctrl.model.change_related_AIDs_force;
      }

      $http({
        method: 'POST',
        url: $ctrl.url,
        data: $ctrl.data,
      })
        .then(function (response) {
          Notifications.add($translate.instant('ORGANIZATION.ORGANIZATION_CHANGED'), 'success');
          $uibModalInstance.close('changed');
          $ctrl.saving = false;
        })
        .catch(function (response) {
          $ctrl.saving = false;
        });
    };
    $ctrl.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
