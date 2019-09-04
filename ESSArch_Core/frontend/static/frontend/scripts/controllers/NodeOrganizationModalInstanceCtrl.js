export default class NodeOrganizationModalInstanceCtrl {
  constructor($translate, $uibModalInstance, appConfig, $http, data, Notifications, Organization) {
    var $ctrl = this;
    $ctrl.node = data.node;
    $ctrl.saving = false;
    $ctrl.$onInit = function() {
      $ctrl.currentOrganization = angular.copy(Organization.getOrganization().id);
      $ctrl.organization = Organization.getOrganization().id;
      $ctrl.organizations = Organization.availableOrganizations();
    };

    $ctrl.save = function() {
      $ctrl.saving = true;
      $http({
        method: 'POST',
        url: appConfig.djangoUrl + 'search/' + data.node._index + '/' + data.node._id + '/change-organization/',
        data: {
          organization: $ctrl.organization,
        },
      })
        .then(function(response) {
          Notifications.add($translate.instant('ORGANIZATION.ORGANIZATION_CHANGED'), 'success');
          $uibModalInstance.close('changed');
          $ctrl.saving = false;
        })
        .catch(function(response) {
          $ctrl.saving = false;
        });
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
