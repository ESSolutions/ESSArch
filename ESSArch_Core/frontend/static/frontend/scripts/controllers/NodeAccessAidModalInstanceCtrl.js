export default class NodeAccessAidModalInstanceCtrl {
  constructor(appConfig, $http, $translate, data, $uibModalInstance, $scope, EditMode, $rootScope, $q, Notifications) {
    const $ctrl = this;
    $ctrl.model = {};

    $ctrl.$onInit = function () {
      $ctrl.aid = data.aid;
      if (data.nodes) {
        $ctrl.nodes = $ctrl.filterNodes(angular.copy(data.nodes));
      } else if (data.node) {
        $ctrl.node = angular.copy(data.node);
      }
      $ctrl.buildForm();
    };

    $ctrl.getAccessAids = function (search) {
      return $http.get(appConfig.djangoUrl + 'access-aids/', {params: {search: search}}).then(function (response) {
        $ctrl.accessAids = response.data;
        return response.data;
      });
    };

    $ctrl.buildForm = function () {
      $ctrl.fields = [
        {
          type: 'uiselect',
          key: 'accessaid',
          templateOptions: {
            required: true,
            options: function () {
              return $ctrl.accessAids;
            },
            valueProp: 'id',
            labelProp: 'name',
            placeholder: $translate.instant('ACCESS.ACCESS_AID'),
            label: $translate.instant('ACCESS.ACCESS_AID'),
            appendToBody: false,
            optionsFunction: function (search) {
              return $ctrl.accessAids;
            },
            refresh: function (search) {
              return $ctrl.getAccessAids(search).then(function () {
                this.options = $ctrl.accessAids;
                return $ctrl.accessAids;
              });
            },
          },
        },
      ];
    };

    $ctrl.filterNodes = function (nodes) {
      const filtered = [];
      nodes.forEach(function (x) {
        if (!angular.isUndefined(x) && x.placeholder !== true && x.type !== 'agent') {
          filtered.push(x);
        }
      });
      return filtered;
    };

    $ctrl.cancel = function () {
      EditMode.disable();
      $uibModalInstance.dismiss('cancel');
    };

    $ctrl.save = function () {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $ctrl.saving = true;
      const structureUnits = [];
      const tags = [];
      if ($ctrl.nodes && $ctrl.nodes.length > 0) {
        $ctrl.nodes.forEach(function (x) {
          if (x._is_structure_unit) {
            structureUnits.push(x);
          } else {
            tags.push(x);
          }
        });
      } else if ($ctrl.node) {
        if ($ctrl.node._is_structure_unit) {
          structureUnits.push($ctrl.node);
        } else {
          tags.push($ctrl.node);
        }
      }
      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'access-aids/' + $ctrl.model.accessaid + '/add-nodes/',
        method: 'POST',
        data: {
          structure_units: structureUnits.map(function (x) {
            return x.id;
          }),
          tags: tags.map(function (x) {
            return x.id;
          }),
        },
      })
        .then(function (response) {
          Notifications.add($translate.instant('ACCESS.ADDED_TO_ACCESS_AID'), 'success');
          $ctrl.saving = false;
          EditMode.disable();
          $uibModalInstance.close(response.data);
        })
        .catch(function (response) {
          $ctrl.nonFieldErrors = response.data.non_field_errors;
          $ctrl.saving = false;
        });
    };

    $ctrl.removeRelation = function () {
      $ctrl.removing = true;
      const structureUnits = [];
      const tags = [];
      if ($ctrl.nodes && $ctrl.nodes.length > 0) {
        $ctrl.nodes.forEach(function (x) {
          if (x._is_structure_unit) {
            structureUnits.push(x);
          } else {
            tags.push(x);
          }
        });
      } else if ($ctrl.node) {
        //console.log("CTRL",$ctrl)
        if ($ctrl.node._is_structure_unit) {
          structureUnits.push($ctrl.node);
        } else {
          tags.push($ctrl.node);
        }
      }

      $rootScope.skipErrorNotification = true;
      $http({
        url: appConfig.djangoUrl + 'access-aids/' + $ctrl.aid.id + '/remove-nodes/',
        method: 'POST',
        data: {
          structure_units: structureUnits.map(function (x) {
            return x.id;
          }),
          tags: tags.map(function (x) {
            return x.id;
          }),
        },
      })
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
