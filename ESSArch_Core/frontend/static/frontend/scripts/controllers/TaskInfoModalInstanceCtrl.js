import moment from 'moment';

export default class TaskInfoModalInstanceCtrl {
  constructor(
    $uibModalInstance,
    data,
    $rootScope,
    $scope,
    PermPermissionStore,
    Task,
    listViewService,
    $uibModal,
    $timeout
  ) {
    const $ctrl = this;
    $scope.myTreeControl = {scope: {}};
    $scope.angular = angular;
    if (data) {
      $ctrl.data = data;
    }

    $ctrl.validations = [];
    $ctrl.$onInit = () => {
      $scope.getTask(data.currentStepTask);
    };

    $ctrl.revokeTask = task => {
      let taskId = angular.copy(task.id);
      Task.revoke({id: taskId}).$promise.then(response => {
        $scope.currentStepTask = null;
        $timeout(function() {
          $scope.getTask({id: taskId});
        }, 1000);
      });
    };

    //Redo step/task
    $scope.myTreeControl.scope.taskStepRedo = function(branch) {
      const branchId = angular.copy(branch.id);
      branch
        .$retry()
        .then(function(response) {
          $scope.currentStepTask = null;
          $timeout(function() {
            $scope.getTask({id: branchId});
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

    /**
     * Validation pipe function for getting validations
     * @param {Object} tableState table state
     */
    $ctrl.getValidations = function(tableState) {
      $scope.validationsLoading = true;
      if ($ctrl.validations.length == 0) {
        $scope.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        $ctrl.validationTableState = tableState;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = (tableState.sort.reverse ? '-' : '') + tableState.sort.predicate;
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, $ctrl.itemsPerPage);
        return Task.validations({
          id: $scope.currentStepTask.id,
          page: paginationParams.pageNumber,
          page_size: paginationParams.number,
          ordering: sorting,
          search: search,
        })
          .$promise.then(function(resource) {
            $ctrl.validations = resource;
            tableState.pagination.numberOfPages = Math.ceil(resource.$httpHeaders('Count') / paginationParams.number); //set the number of pages so the pagination can update
            tableState.pagination.totalItemCount = resource.$httpHeaders('Count');
            $scope.validationsLoading = false;
            return resource;
          })
          .catch(function(response) {
            $scope.validationsLoading = false;
            return response;
          });
      }
    };

    $scope.getTask = function(branch) {
      $scope.stepTaskLoading = true;
      return Task.get({id: branch.id}).$promise.then(function(data) {
        if (data.time_started !== null && data.time_done !== null) {
          const started = moment(data.time_started);
          const done = moment(data.time_done);
          data.duration = moment.utc(done.diff(started)).format('HH:mm:ss.SSS');
        } else {
          data.duration = null;
        }
        $scope.currentStepTask = angular.copy(data);
        $scope.stepTaskLoading = false;
        $ctrl.getValidations($ctrl.validationTableState);
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
