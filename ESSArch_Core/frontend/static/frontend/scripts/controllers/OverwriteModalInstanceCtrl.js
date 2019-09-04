export default class OverwriteModalInstanceCtrl {
  constructor($uibModalInstance, data, Profile, SA, Notifications, $translate) {
    const $ctrl = this;
    if (data.file) {
      $ctrl.file = data.file;
    }
    if (data.type) {
      $ctrl.type = data.type;
    }
    if (data.profile) {
      $ctrl.profile = data.profile;
    }
    $ctrl.overwriteProfile = function() {
      return Profile.update($ctrl.profile).$promise.then(function(resource) {
        Notifications.add($translate.instant('IMPORT.PROFILE_IMPORTED', resource), 'success', 5000, {isHtml: true});
        $ctrl.data = {
          status: 'overwritten',
        };
        $uibModalInstance.close($ctrl.data);
        return resource;
      });
    };
    $ctrl.overwriteSa = function() {
      return SA.update($ctrl.profile)
        .$promise.then(function(resource) {
          Notifications.add($translate.instant('IMPORT.SA_IMPORTED', resource), 'success', 5000, {isHtml: true});
          $ctrl.data = {
            status: 'overwritten',
          };
          $uibModalInstance.close($ctrl.data);
          return resource;
        })
        .catch(function(response) {
          if (response.status === 405) {
            Notifications.add(
              $translate.instant('IMPORT.SA_IS_PUBLISHED_CANNOT_BE_OVERWRITTEN', $ctrl.profile),
              'error'
            );
          }
        });
    };
    $ctrl.overwrite = function() {
      $ctrl.data = {
        status: 'overwritten',
      };
      $uibModalInstance.close($ctrl.data);
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
