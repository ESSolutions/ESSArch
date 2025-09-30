export default class AccessAidModalInstanceCtrl {
  constructor(appConfig, $http, $translate, data, $uibModalInstance, $scope, EditMode, Utils, $rootScope) {
    const $ctrl = this;
    $ctrl.accessAid = {};
    $ctrl.options = {};
    $ctrl.$onInit = function () {
      if (!data.remove) {
        if (data.accessAid) {
          $ctrl.accessAid = angular.copy(data.accessAid);
          $ctrl.accessAid.type = angular.copy(data.accessAid.type.id);
        }

        $ctrl.getAccessAidTypes().then(function (response) {
          EditMode.enable();
          $ctrl.buildForm();
        });
      } else {
        if (data.accessAid) {
          $ctrl.accessAid = angular.copy(data.accessAid);
        }
      }
    };

    $ctrl.getAccessAidTypes = function (search) {
      return $http.get(appConfig.djangoUrl + 'access-aid-types/').then(function (response) {
        $ctrl.accessAidTypes = response.data;
        return response.data;
      });
    };

    $ctrl.buildForm = function () {
      $ctrl.fields = [
        {
          type: 'input',
          key: 'name',
          templateOptions: {
            focus: true,
            label: $translate.instant('NAME'),
            required: true,
            maxlength: 255,
          },
        },
        {
          type: 'select',
          key: 'type',
          templateOptions: {
            required: true,
            label: $translate.instant('TYPE'),
            labelProp: 'name',
            valueProp: 'id',
            options: $ctrl.accessAidTypes,
            notNull: true,
          },
          defaultValue: $ctrl.accessAidTypes.length > 0 ? $ctrl.accessAidTypes[0].id : null,
        },
        {
          type: 'textarea',
          key: 'description',
          templateOptions: {
            label: $translate.instant('DESCRIPTION'),
            rows: 3,
          },
        },
        {
          templateOptions: {
            label: $translate.instant('ACCESS.SECURITY_LEVEL'),
            type: 'number',
            required: false,
            min: 0,
            max: 5,
          },
          type: 'input',
          key: 'security_level',
        },
        {
          templateOptions: {
            label: $translate.instant('ACCESS.LINK'),
            required: false,
          },
          type: 'input',
          key: 'link',
        },
      ];
    };

    $ctrl.cancel = function () {
      EditMode.disable();
      $uibModalInstance.dismiss('cancel');
    };
    $ctrl.create = function () {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.creating = true;
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'access-aids/',
        method: 'POST',
        data: $ctrl.accessAid,
      })
        .then(function (response) {
          $ctrl.creating = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function (response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.creating = false;
        });
    };
    $ctrl.save = function () {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.saving = true;
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'access-aids/' + data.accessAid.id + '/',
        method: 'PATCH',
        data: Utils.getDiff(data.accessAid, $ctrl.accessAid, {map: {type: 'id'}}),
      })
        .then(function (response) {
          $ctrl.saving = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function () {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.saving = false;
        });
    };

    $ctrl.remove = function () {
      $ctrl.removing = true;
      $rootScope.skipErrorNotification = true;
      $http
        .delete(appConfig.djangoUrl + 'access-aids/' + $ctrl.accessAid.id + '/')
        .then(function (response) {
          $ctrl.removing = false;
          EditMode.disable();
          $uibModalInstance.close('removed');
        })
        .catch(function (response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.removing = false;
        });
    };

    $scope.$on('modal.closing', function (event, reason, closed) {
      if (
        (data.allow_close === null || angular.isUndefined(data.allow_close) || data.allow_close !== true) &&
        (reason === 'cancel' || reason === 'backdrop click' || reason === 'escape key press')
      ) {
        const message = $translate.instant('UNSAVED_DATA_WARNING');
        if (!confirm(message)) {
          event.preventDefault();
        } else {
          EditMode.disable();
        }
      }
    });
  }
}
