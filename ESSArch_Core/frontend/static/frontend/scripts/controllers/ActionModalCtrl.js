export default class ActionModalCtrl {
    constructor($scope, $uibModalInstance, currentStepTask) {
        $scope.currentStepTask = currentStepTask;
        $scope.ok = () => {
            $uibModalInstance.close('remove');
        };
        $scope.idCopied = false;
        $scope.idCopyDone = function () {
            $scope.idCopied = true;
          };
    }
  }