import moment from 'moment';

export default class ActionModalCtrl {
  constructor($scope, $rootScope, $uibModalInstance, currentStepTask) {
    if (currentStepTask.time_started !== null && currentStepTask.time_done !== null) {
      const started = moment(currentStepTask.time_started);
      const done = moment(currentStepTask.time_done);
      currentStepTask.duration = moment.utc(done.diff(started)).format('HH:mm:ss.SSS');
    } else {
      currentStepTask.duration = null;
    }

    $scope.mapStepStateProgress = $rootScope.mapStepStateProgress;
    if (currentStepTask.time_started !== null && currentStepTask.time_done !== null) {
      const started = moment(currentStepTask.time_started);
      const done = moment(currentStepTask.time_done);
      currentStepTask.duration = moment.utc(done.diff(started)).format('HH:mm:ss.SSS');
    } else {
      currentStepTask.duration = null;
    }

    $scope.currentStepTask = currentStepTask;
    $scope.ok = () => {
      $uibModalInstance.close('remove');
    };
    $scope.idCopied = false;
    $scope.idCopyDone = function () {
      $scope.idCopied = true;
    };

    $scope.getArgsString = function (args) {
      if (!angular.isUndefined(args)) {
        return args
          .map(function (x) {
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
  }
}
