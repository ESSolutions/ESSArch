export default class ActionModalCtrl {
    constructor($scope, $uibModalInstance, validations) {
        $scope.selected = validations;
        $scope.ok = () => {
            $uibModalInstance.close('remove');
        };
    }
  }