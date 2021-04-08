export default class SaveWorkflowModalInstanceCtrl {
  constructor($uibModalInstance, data) {
    const $ctrl = this;
    $ctrl.data = data;
    if ($ctrl.data.currentProfile.name) {
      $ctrl.workflowName = $ctrl.data.currentProfile.name;
    } else {
      $ctrl.workflowName = '';
    }

    if ($ctrl.data.currentProfile.status) {
      $ctrl.status = $ctrl.data.currentProfile.status;
    } else {
      $ctrl.status = '';
    }
    $ctrl.res = {action_workflow_name: '', action_workflow_status: ''};
    $ctrl.save = function () {
      if ($ctrl.workflowName.length > 0 && $ctrl.status.length > 0) {
        $ctrl.res.action_workflow_name = $ctrl.workflowName;
        $ctrl.res.action_workflow_status = $ctrl.status;
        $uibModalInstance.close($ctrl.res);
      }
    };
    $ctrl.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
