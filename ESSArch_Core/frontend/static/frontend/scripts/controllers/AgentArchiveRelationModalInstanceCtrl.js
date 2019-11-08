export default class AgentArchiveRelationModalInstanceCtrl {
  constructor($uibModalInstance, appConfig, data, $http, EditMode, $scope, $translate, $filter, $rootScope) {
    const $ctrl = this;
    $ctrl.relationTemplate = {
      description: '',
      start_date: null,
      end_date: null,
      archive: null,
    };
    $ctrl.options = {};
    $ctrl.data = data;
    $ctrl.fields = [];
    $ctrl.$onInit = function() {
      if (data.agent) {
        $ctrl.agent = angular.copy(data.agent);
      }
      if (data.relation) {
        $ctrl.relation = angular.copy(data.relation);
        $ctrl.relation.archive = data.relation.archive._id;
        $ctrl.relation.type = data.relation.type.id;
      } else {
        $ctrl.relation = $ctrl.relationTemplate;
      }
      return $http({
        url: appConfig.djangoUrl + 'agent-tag-relation-types/',
        params: {pager: 'none'},
        method: 'GET',
      }).then(function(response) {
        $ctrl.options.type = response.data;
        $ctrl.loadForm();
        EditMode.enable();
        return response.data;
      });
    };

    $ctrl.getArchives = function(search) {
      return $http({
        url: appConfig.djangoUrl + 'tags/',
        mathod: 'GET',
        params: {page: 1, page_size: 10, index: 'archive', search: search},
      }).then(function(response) {
        $ctrl.options.archives = response.data.map(function(x) {
          x.current_version.name_with_dates =
            x.current_version.name +
            (x.current_version.start_date !== null || x.current_version.end_date != null
              ? ' (' +
                (x.current_version.start_date !== null ? $filter('date')(x.current_version.start_date, 'yyyy') : '') +
                ' - ' +
                (x.current_version.end_date !== null ? $filter('date')(x.current_version.end_date, 'yyyy') : '') +
                ')'
              : '');
          return x.current_version;
        });
        return $ctrl.options.archives;
      });
    };
    $ctrl.loadForm = function() {
      $ctrl.fields = [
        {
          type: 'uiselect',
          key: 'archive',
          templateOptions: {
            required: true,
            options: function() {
              return $ctrl.options.archives;
            },
            valueProp: 'id',
            labelProp: 'name_with_dates',
            placeholder: $translate.instant('ACCESS.ARCHIVE'),
            label: $translate.instant('ACCESS.ARCHIVE'),
            appendToBody: false,
            optionsFunction: function(search) {
              return $ctrl.options.archives;
            },
            refresh: function(search) {
              return $ctrl.getArchives(search).then(function() {
                this.options = $ctrl.options.archives;
                return $ctrl.options.archives;
              });
            },
          },
        },
        {
          type: 'select',
          key: 'type',
          templateOptions: {
            label: $translate.instant('TYPE'),
            options: $ctrl.options.type,
            required: true,
            labelProp: 'name',
            valueProp: 'id',
            defaultValue: $ctrl.options.type.length > 0 ? $ctrl.options.type[0].id : null,
            notNull: true,
          },
        },
        {
          className: 'row m-0',
          fieldGroup: [
            {
              className: 'col-xs-12 col-sm-6 px-0 pr-md-base',
              type: 'datepicker',
              key: 'start_date',
              templateOptions: {
                label: $translate.instant('ACCESS.VALID_DATE_START'),
                appendToBody: false,
                dateFormat: 'YYYY-MM-DD',
              },
            },
            {
              className: 'col-xs-12 col-sm-6 px-0 pl-md-base',
              type: 'datepicker',
              key: 'end_date',
              templateOptions: {
                label: $translate.instant('ACCESS.VALID_DATE_END'),
                appendToBody: false,
                dateFormat: 'YYYY-MM-DD',
              },
            },
          ],
        },
        {
          key: 'description',
          type: 'textarea',
          templateOptions: {
            label: $translate.instant('DESCRIPTION'),
            rows: 3,
          },
        },
      ];
    };

    $ctrl.add = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.adding = true;
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'agents/' + $ctrl.agent.id + '/archives/',
        method: 'POST',
        data: $ctrl.relation,
      })
        .then(function(response) {
          $ctrl.adding = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.adding = false;
          EditMode.disable();
        });
    };

    $ctrl.save = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.saving = true;
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'agents/' + $ctrl.agent.id + '/archives/' + $ctrl.relation.id + '/',
        method: 'PATCH',
        data: $ctrl.relation,
      })
        .then(function(response) {
          $ctrl.saving = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.saving = false;
          EditMode.disable();
        });
    };

    $ctrl.remove = function() {
      $ctrl.removing = true;
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'agents/' + $ctrl.agent.id + '/archives/' + $ctrl.relation.id + '/',
        method: 'DELETE',
      })
        .then(function(response) {
          $ctrl.removing = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function(response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.removing = false;
          EditMode.disable();
        });
    };

    $ctrl.cancel = function() {
      EditMode.disable();
      $uibModalInstance.dismiss('cancel');
    };
    $scope.$on('modal.closing', function(event, reason, closed) {
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
