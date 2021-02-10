export default class ActionModalCtrl {
    constructor($scope, $uibModalInstance, currentStepTask) {
        $scope.currentStepTask = currentStepTask;
        $scope.ok = () => {
            $uibModalInstance.close('remove');
        };
    }
  }