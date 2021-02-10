export default class ActionModalCtrl {
    constructor($scope, $uibModalInstance, currentStepTask) {
        $scope.selected = currentStepTask;
        $scope.ok = () => {
            $uibModalInstance.close('remove');
        };
    }
  }