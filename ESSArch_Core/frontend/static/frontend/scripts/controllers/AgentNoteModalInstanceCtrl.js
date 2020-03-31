export default class AgentNoteModalInstanceCtrl {
  constructor($uibModalInstance, $scope, $translate, $http, appConfig, data, EditMode, $rootScope) {
    const $ctrl = this;
    $ctrl.note;
    $ctrl.noteTemplate = {
      create_date: new Date(),
      href: '',
      revise_date: null,
      text: null,
      type: null,
    };
    $ctrl.fields = [];
    $ctrl.resetNote = function () {
      $ctrl.note = angular.copy($ctrl.noteTemplate);
    };

    $ctrl.getItemById = (id, list) => {
      let type = null;
      list.forEach((item) => {
        if (item.id === id) {
          type = item;
        }
      });
      return type;
    };

    $ctrl.$onInit = function () {
      let history = false;
      if (data.note && data.note.type.history) {
        history = data.note.type.history;
      } else if (data.history) {
        history = data.history;
      }
      return $http({
        url: appConfig.djangoUrl + 'agent-note-types/',
        params: {pager: 'none', history},
        method: 'GET',
      }).then(function (response) {
        $ctrl.typeOptions = response.data;
        EditMode.enable();
        if (data.note) {
          const note = angular.copy(data.note);
          note.type = data.note.type.id;
          $ctrl.note = angular.copy(note);
        } else {
          $ctrl.resetNote();
        }
        $ctrl.loadForm();
      });
    };

    $ctrl.loadForm = function () {
      $ctrl.fields = [
        {
          type: 'select',
          key: 'type',
          templateOptions: {
            label: $translate.instant('TYPE'),
            options: $ctrl.typeOptions,
            required: true,
            labelProp: 'name',
            valueProp: 'id',
            defaultValue: $ctrl.typeOptions.length > 0 ? $ctrl.typeOptions[0].id : null,
            focus: true,
            notNull: true,
          },
        },
        {
          key: 'text',
          type: 'textarea',
          templateOptions: {
            label: $translate.instant('ACCESS.TEXT'),
            rows: 3,
            required: true,
          },
        },
        {
          key: 'href',
          type: 'input',
          templateOptions: {
            label: $translate.instant('ACCESS.HREF'),
          },
        },
        {
          type: 'datepicker',
          key: 'create_date',
          templateOptions: {
            label: $translate.instant('CREATE_DATE'),
            appendToBody: false,
            required: true,
          },
        },
        {
          type: 'datepicker',
          key: 'revise_date',
          templateOptions: {
            label: $translate.instant('ACCESS.REVISE_DATE'),
            appendToBody: false,
          },
        },
      ];
    };

    $ctrl.add = function () {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.adding = true;
      const notes = angular.copy(data.agent.notes);
      notes.forEach(function (x) {
        if (typeof x.type === 'object') {
          x.type = x.type.id;
        }
      });
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'agents/' + data.agent.id + '/',
        method: 'PATCH',
        data: {notes: [$ctrl.note].concat(notes)},
      })
        .then(function (response) {
          $ctrl.adding = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function (response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          if (response.data.notes) {
            if (angular.isArray($ctrl.nonFieldErrors)) {
              $ctrl.nonFieldErrors = $ctrl.nonFieldErrors.concat(response.data.notes);
            } else {
              $ctrl.nonFieldErrors = response.data.notes;
            }
          }
          $ctrl.adding = false;
        });
    };

    $ctrl.save = function () {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.saving = true;
      const notes = angular.copy(data.agent.notes);
      notes.forEach(function (x, idx, array) {
        if (typeof x.type === 'object') {
          x.type = x.type.id;
        }
        if (x.id === $ctrl.note.id) {
          array[idx] = $ctrl.note;
        }
      });
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'agents/' + data.agent.id + '/',
        method: 'PATCH',
        data: {notes: notes},
      })
        .then(function (response) {
          $ctrl.saving = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function (response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          if (response.data.notes) {
            if (angular.isArray($ctrl.nonFieldErrors)) {
              $ctrl.nonFieldErrors = $ctrl.nonFieldErrors.concat(response.data.notes);
            } else {
              $ctrl.nonFieldErrors = response.data.notes;
            }
          }
          $ctrl.saving = false;
        });
    };

    $ctrl.remove = function () {
      $ctrl.removing = true;
      let toRemove = null;
      const notes = angular.copy(data.agent.notes);
      notes.forEach(function (x, idx, array) {
        if (typeof x.type === 'object') {
          x.type = x.type.id;
        }
        if (x.id === $ctrl.note.id) {
          toRemove = idx;
        }
      });
      if (toRemove !== null) {
        notes.splice(toRemove, 1);
      }
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'agents/' + data.agent.id + '/',
        method: 'PATCH',
        data: {notes: notes},
      })
        .then(function (response) {
          $ctrl.removing = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function (response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          if (response.data.notes) {
            if (angular.isArray($ctrl.nonFieldErrors)) {
              $ctrl.nonFieldErrors = $ctrl.nonFieldErrors.concat(response.data.notes);
            } else {
              $ctrl.nonFieldErrors = response.data.notes;
            }
          }
          $ctrl.removing = false;
        });
    };

    $ctrl.cancel = function () {
      EditMode.disable();
      $uibModalInstance.dismiss('cancel');
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
