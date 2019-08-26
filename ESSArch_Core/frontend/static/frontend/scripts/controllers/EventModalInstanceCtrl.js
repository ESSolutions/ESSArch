export default class EventModalInstanceCtrl {
  constructor(appConfig, $http, $translate, data, $uibModalInstance, $scope, EditMode, Utils, $rootScope) {
    var $ctrl = this;
    $ctrl.event = {};
    $ctrl.$onInit = function() {
      if (!data.remove) {
        if (data.event) {
          $ctrl.event = angular.copy(data.event);
        }
        $ctrl.getEventTypes().then(function(response) {
          $ctrl.buildForm();
        });
      } else {
        if (data.event) {
          $ctrl.event = angular.copy(data.event);
        }
      }
    };

    $ctrl.getEventTypes = function(search) {
      return $http
        .get(appConfig.djangoUrl + 'event-types/', {params: {category: 1, search: search}})
        .then(function(response) {
          $ctrl.eventTypes = response.data;
          return response.data;
        });
    };

    $ctrl.buildForm = function() {
      $ctrl.fields = [
        {
          type: 'select',
          key: 'eventType',
          templateOptions: {
            required: true,
            label: $translate.instant('EVENT.EVENTTYPE'),
            labelProp: 'eventDetail',
            valueProp: 'eventType',
            options: $ctrl.eventTypes,
            notNull: true,
          },
          defaultValue: $ctrl.eventTypes.length > 0 ? $ctrl.eventTypes[0].id : null,
        },
        {
          type: 'datepicker',
          key: 'eventDateTime',
          templateOptions: {
            label: $translate.instant('EVENT.EVENTTIME'),
            appendToBody: false,
            required: true,
            minView: 'minute',
            dateFormat: 'YYYY-MM-DD HH:mm:ss',
          },
          defaultValue: new Date(),
        },
        {
          type: 'select',
          key: 'eventOutcome',
          templateOptions: {
            required: true,
            label: $translate.instant('RESULT'),
            labelProp: 'name',
            valueProp: 'id',
            options: [
              {
                id: 0,
                name: $translate.instant('EVENT.EVENT_SUCCESS'),
              },
              {
                id: 1,
                name: $translate.instant('EVENT.EVENT_FAILURE'),
              },
            ],
            notNull: true,
          },
          defaultValue: 0,
        },
        {
          type: 'textarea',
          key: 'eventOutcomeDetailNote',
          templateOptions: {
            label: $translate.instant('DESCRIPTION'),
            rows: 3,
          },
        },
      ];
    };

    $ctrl.cancel = function() {
      EditMode.disable();
      $uibModalInstance.dismiss('cancel');
    };
    $ctrl.create = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.creating = true;
      $rootScope.skipErrorNotification = true;
      if (data.delivery) {
        $ctrl.event.delivery = data.delivery.id;
      }
      if (data.transfer) {
        $ctrl.event.transfer = data.transfer.id;
      }
      $http({
        url: appConfig.djangoUrl + 'events/',
        method: 'POST',
        data: $ctrl.event,
      })
        .then(function(response) {
          $ctrl.creating = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.creating = false;
        });
    };
    $ctrl.save = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.saving = true;
      $rootScope.skipErrorNotification = true;
      var saveData = Utils.getDiff(data.event, $ctrl.event, {map: {type: 'id'}});
      if (!angular.isUndefined(saveData.eventOutcomeDetailNote) && saveData.eventOutcomeDetailNote === null) {
        saveData.eventOutcomeDetailNote = '';
      }
      $http({
        url: appConfig.djangoUrl + 'events/' + data.event.id + '/',
        method: 'PATCH',
        data: saveData,
      })
        .then(function(response) {
          $ctrl.saving = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function() {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.saving = false;
        });
    };

    $ctrl.remove = function() {
      $ctrl.removing = true;
      $rootScope.skipErrorNotification = true;
      $http
        .delete(appConfig.djangoUrl + 'events/' + $ctrl.event.id)
        .then(function(response) {
          $ctrl.removing = false;
          EditMode.disable();
          $uibModalInstance.close('removed');
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.removing = false;
        });
    };

    $scope.$on('modal.closing', function(event, reason, closed) {
      if (
        (data.allow_close === null || angular.isUndefined(data.allow_close) || data.allow_close !== true) &&
        (reason === 'cancel' || reason === 'backdrop click' || reason === 'escape key press')
      ) {
        var message = $translate.instant('UNSAVED_DATA_WARNING');
        if (!confirm(message)) {
          event.preventDefault();
        } else {
          EditMode.disable();
        }
      }
    });
  }
}
