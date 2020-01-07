import moment from 'moment';

export default class StepInfoModalInstanceCtrl {
  constructor($uibModalInstance, data, $rootScope, $scope, PermPermissionStore, Step, $uibModal) {
    const $ctrl = this;
    $scope.myTreeControl = {scope: {}};
    if (data) {
      $ctrl.data = data;
    }

    $ctrl.validations = [];
    $ctrl.$onInit = () => {
      if (data.currentStepTask.time_started !== null && data.currentStepTask.time_done !== null) {
        const started = moment(data.currentStepTask.time_started);
        const done = moment(data.currentStepTask.time_done);
        data.currentStepTask.duration = moment.utc(done.diff(started)).format('HH:mm:ss.SSS');
      } else {
        data.currentStepTask.duration = null;
      }
      $scope.currentStepTask = angular.copy(data.currentStepTask);
    };

    //Undo step/task
    $scope.myTreeControl.scope.taskStepUndo = function(branch) {
      branch
        .$undo()
        .then(function(response) {
          if ($scope.currentStepTask.flow_type === 'task') {
            $scope.getTask($scope.currentStepTask);
          } else {
            $scope.getStep($scope.currentStepTask);
          }
          $timeout(function() {
            $scope.statusViewUpdate($scope.ip);
          }, 1000);
        })
        .catch(function() {
          console.log('error');
        });
    };
    //Redo step/task
    $scope.myTreeControl.scope.taskStepRedo = function(branch) {
      branch
        .$retry()
        .then(function(response) {
          if ($scope.currentStepTask.flow_type === 'task') {
            $scope.getTask($scope.currentStepTask);
          } else {
            $scope.getStep($scope.currentStepTask);
          }
          $timeout(function() {
            $scope.statusViewUpdate($scope.ip);
          }, 1000);
        })
        .catch(function() {
          console.log('error');
        });
    };

    $ctrl.tracebackCopied = false;
    $ctrl.copied = function() {
      $ctrl.tracebackCopied = true;
    };
    $ctrl.idCopied = false;
    $ctrl.idCopyDone = function() {
      $ctrl.idCopied = true;
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
    $ctrl.mapStepStateProgress = $rootScope.mapStepStateProgress;
    $scope.extendedEqual = function(specification_data, model) {
      let returnValue = true;
      for (const prop in model) {
        if (model[prop] == '' && angular.isUndefined(specification_data[prop])) {
          returnValue = false;
        }
      }
      if (returnValue) {
        return angular.equals(specification_data, model);
      } else {
        return true;
      }
    };

    $scope.checkPermission = function(permissionName) {
      return !angular.isUndefined(PermPermissionStore.getPermissionDefinition(permissionName));
    };

    // build comma separated args display string
    $ctrl.getArgsString = function(args) {
      if (!angular.isUndefined(args)) {
        return args
          .map(function(x) {
            if (x === null) {
              return 'null';
            } else {
              return x;
            }
          })
          .join(', ');
      } else {
        return '';
      }
    };

    $scope.getStep = function(branch) {
      $scope.stepTaskLoading = true;
      return Step.get({id: branch.id}).$promise.then(function(data) {
        if (data.time_started !== null && data.time_done !== null) {
          const started = moment(data.time_started);
          const done = moment(data.time_done);
          data.duration = moment.utc(done.diff(started)).format('HH:mm:ss.SSS');
        } else {
          data.duration = null;
        }
        $scope.currentStepTask = data;
        $scope.stepTaskLoading = false;
        return data;
      });
    };
    //Modal functions
    $scope.tracebackModal = function() {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/modals/task_traceback_modal.html',
        scope: $scope,
        size: 'lg',
        controller: 'ModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {},
        },
      });
      modalInstance.result.then(
        function(data) {},
        function() {}
      );
    };
  }
}
