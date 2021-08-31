export default class SaveWorkflowModalInstanceCtrl {
  constructor($uibModalInstance, data) {
    const $ctrl = this;
    $ctrl.data = data;
    if (!angular.isUndefined($ctrl.data) && $ctrl.data !== null) {
      if (!angular.isUndefined($ctrl.data.workflow) && $ctrl.data.workflow !== null) {
        if (!angular.isUndefined($ctrl.data.workflow.name) && $ctrl.data.workflow.name !== null) {
          $ctrl.workflowName = $ctrl.data.workflow.name;
        }
      }
    } else {
      $ctrl.workflowName = '';
    }
    if (!angular.isUndefined($ctrl.data) && $ctrl.data !== null) {
      if (!angular.isUndefined($ctrl.data.workflow) && $ctrl.data.workflow !== null) {
        if (!angular.isUndefined($ctrl.data.workflow.status) && $ctrl.data.workflow.status !== null) {
          $ctrl.status = $ctrl.data.workflow.status;
        }
      }
    } else {
      $ctrl.status = '';
    }
    $ctrl.res = {action_workflow_name: '', action_workflow_status: ''};
    $ctrl.save = function () {
      if ($ctrl.workflowName.length > 0 && $ctrl.status.length > 0) {
        $ctrl.res.action_workflow_name = $ctrl.workflowName;
        $ctrl.res.action_workflow_status = $ctrl.status;
        $uibModalInstance.close($ctrl.res);
        $uibModalInstance.dismiss('cancel');
      }
    };
    $ctrl.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
