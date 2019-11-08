export default class AddNodeModalInstanceCtrl {
  constructor(
    Search,
    $translate,
    $uibModalInstance,
    appConfig,
    $http,
    data,
    $scope,
    Notifications,
    $rootScope,
    EditMode
  ) {
    const $ctrl = this;
    $ctrl.node = data.node.original;
    $ctrl.nodeFields = [];
    $ctrl.typeOptions = [];
    $ctrl.newNode = {
      index: 'component',
      notes: [],
      identifiers: [],
    };
    $ctrl.options = {};
    $ctrl.nodeFields = [];
    $ctrl.types = [];
    $ctrl.custom_fields_template = [];

    $ctrl.$onInit = function() {
      $http
        .get(appConfig.djangoUrl + 'tag-version-types/', {params: {archive_type: false, pager: 'none'}})
        .then(function(response) {
          let url = appConfig.djangoUrl;
          if (data.node.original._is_structure_unit) {
            url = angular.copy(url) + 'structure-units/';
          } else {
            url = angular.copy(url) + 'search/';
          }
          $http.head(url + data.node.original.id + '/children/').then(function(childrenResponse) {
            const count = parseInt(childrenResponse.headers('Count'));
            if (!isNaN(count)) {
              $ctrl.newNode.reference_code = (count + 1).toString();
            }
            EditMode.enable();
            $ctrl.typeOptions = response.data;
            $ctrl.loadForm();
          });
        });
    };

    $ctrl.getType = id => {
      let type = null;
      $ctrl.typeOptions.forEach(x => {
        if (id === x.pk) {
          type = x;
        }
      });
      return type;
    };

    $ctrl.getInformationPackages = function(search) {
      return $http({
        url: appConfig.djangoUrl + 'information-packages/',
        mathod: 'GET',
        params: {page: 1, page_size: 10, search: search, archived: true, view_type: 'flat'},
      }).then(function(response) {
        $ctrl.options.ips = response.data;
        return $ctrl.options.ips;
      });
    };

    let isIpType = type => {
      let ipType = false;
      $ctrl.typeOptions.forEach(x => {
        if (x.pk === type && x.information_package_type) {
          ipType = true;
        }
      });
      return ipType;
    };

    $ctrl.loadForm = function() {
      $ctrl.nodeFields = [
        {
          templateOptions: {
            type: 'text',
            label: $translate.instant('LABEL'),
            required: true,
            focus: true,
          },
          type: 'input',
          key: 'name',
        },
        {
          templateOptions: {
            label: $translate.instant('TYPE'),
            required: true,
            options: $ctrl.typeOptions,
            valueProp: 'pk',
            labelProp: 'name',
            notNull: $ctrl.typeOptions.length > 0,
          },
          defaultValue: $ctrl.typeOptions.length > 0 ? $ctrl.typeOptions[0].pk : null,
          type: 'select',
          key: 'type',
          expressionProperties: {
            'templateOptions.onChange': function($modelValue) {
              $ctrl.custom_fields_template = $ctrl.getType($modelValue).custom_fields_template;
            },
          },
        },
        {
          templateOptions: {
            label: $translate.instant('ACCESS.REFERENCE_CODE'),
            type: 'text',
            required: true,
          },
          type: 'input',
          key: 'reference_code',
        },
        {
          key: 'description',
          type: 'textarea',
          templateOptions: {
            label: $translate.instant('DESCRIPTION'),
            rows: 3,
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
                label: $translate.instant('START_DATE'),
                appendToBody: false,
              },
            },
            {
              className: 'col-xs-12 col-sm-6 px-0 pl-md-base',
              type: 'datepicker',
              key: 'end_date',
              templateOptions: {
                label: $translate.instant('END_DATE'),
                appendToBody: false,
              },
            },
          ],
        },
        {
          type: 'uiselect',
          key: 'information_package',
          hideExpression: () => {
            return !isIpType($ctrl.newNode.type);
          },
          templateOptions: {
            options: function() {
              return $ctrl.options.ips;
            },
            valueProp: 'id',
            labelProp: 'label',
            placeholder: $translate.instant('INFORMATION_PACKAGE'),
            label: $translate.instant('INFORMATION_PACKAGE'),
            appendToBody: false,
            refresh: function(search) {
              if (angular.isUndefined(search) || search === null || search === '') {
                search = '';
              }
              return $ctrl.getInformationPackages(search).then(function() {
                this.options = $ctrl.options.ips;
                return $ctrl.options.ips;
              });
            },
          },
        },
      ];
    };

    $ctrl.changed = function() {
      return !angular.equals($ctrl.newNode, {});
    };

    $ctrl.submit = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      if ($ctrl.changed()) {
        $ctrl.submitting = true;
        const params = angular.extend($ctrl.newNode, {
          archive: data.archive,
          structure: data.structure,
          location: null,
        });
        if ($ctrl.node._is_structure_unit) params.structure_unit = $ctrl.node._id;
        else {
          params.parent = $ctrl.node._id;
        }

        $rootScope.skipErrorNotification = true;
        Search.addNode(params)
          .then(function(response) {
            $ctrl.submitting = false;
            Notifications.add($translate.instant('ACCESS.NODE_ADDED'), 'success');
            EditMode.disable();
            $uibModalInstance.close(response.data);
          })
          .catch(function(response) {
            $ctrl.nonFieldErrors = response.data.non_field_errors;
            $ctrl.submitting = false;
          });
      }
    };
    $ctrl.cancel = function() {
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
