import moment from 'moment';

export default class StateTreeCtrl {
  constructor(
    $scope,
    $translate,
    Step,
    Task,
    appConfig,
    $state,
    $timeout,
    $interval,
    PermPermissionStore,
    $q,
    $uibModal,
    $log,
    StateTree,
    $rootScope,
    $transitions,
    listViewService
  ) {
    const vm = this;
    let stateInterval;
    $scope.angular = angular;
    $scope.myTreeControl = {};
    $scope.myTreeControl.scope = this;
    $scope.tree_data = [];
    $scope.newPage = true;
    $scope.angular = angular;
    $scope.statusShow = false;
    $scope.eventShow = false;

    $scope.$translate = $translate;
    vm.displayedJobs = [];

    vm.$onChanges = function () {
      $scope.tree_data = [];
      $scope.paginationParams = {};
      $scope.columnFilters = {};
      $scope.ip = vm.ip;
      $scope.responsible = $translate.instant('RESPONSIBLE');
      $scope.label = $translate.instant('LABEL');
      $scope.date = $translate.instant('DATE');
      $scope.state = $translate.instant('STATE');
      $scope.status = $translate.instant('STATUS');
      $scope.information_package = $translate.instant('INFORMATION_PACKAGE');
      $scope.expanding_property = {
        field: 'label',
        displayName: $scope.label,
      };
      $scope.col_defs = [
        {
          field: 'responsible',
          displayName: $scope.responsible,
        },
        {
          cellTemplate: '<div ng-include src="\'static/frontend/views/task_pagination.html\'"></div>',
        },
        {
          field: 'time_started',
          displayName: $scope.date,
        },
        {
          field: 'progress',
          displayName: $scope.status,
          cellTemplate: '<div ng-include src="\'static/frontend/views/step_task_progressbar.html\'"></div>',
        },
      ];
      if ($state.includes('**.storageMigration.**')) {
        $scope.col_defs.push({
          field: 'information_package_str',
          displayName: $scope.information_package,
        });
      }
      if ($scope.checkPermission('WorkflowEngine.can_retry')) {
        $scope.col_defs.push({
          cellTemplate: '<div ng-include src="\'static/frontend/views/workflow/redo.html\'"></div>',
        });
      }

      $interval.cancel(stateInterval);
      stateInterval = $interval(function () {
        $scope.statusViewUpdate($scope.tableState);
      }, appConfig.stateInterval);
    };

    vm.$onDestroy = function () {
      $interval.cancel(stateInterval);
    };

    //Cancel update intervals on state change
    $transitions.onSuccess({}, function ($transition) {
      $interval.cancel(stateInterval);
    });

    // Key codes
    const arrowUp = 38;
    const arrowDown = 40;
    const escape = 27;
    const enter = 13;
    const space = 32;

    /**
     * Handle keydown events for state view table
     * @param {Event} e
     */
    $scope.myTreeControl.scope.stateTableKeydownListener = function (e, branch) {
      switch (e.keyCode) {
        case arrowDown:
          e.preventDefault();
          e.target.nextElementSibling.focus();
          break;
        case arrowUp:
          e.preventDefault();
          e.target.previousElementSibling.focus();
          break;
        case enter:
          e.preventDefault();
          $scope.stepTaskClick(branch);
          break;
        case space:
          e.preventDefault();
          if (branch.flow_type != 'task') {
            if (branch.expanded) {
              branch.expanded = false;
            } else {
              branch.expanded = true;
              $scope.stepClick(branch);
            }
          }
          break;
        case escape:
          e.preventDefault();
          if ($scope.ip) {
            closeContentViews();
          }
          document.getElementById('list-view').focus();
          break;
      }
    };

    //Redo step/task
    $scope.myTreeControl.scope.taskStepRedo = function (branch) {
      branch
        .$retry()
        .then(function (response) {
          $timeout(function () {
            $scope.statusViewUpdate($scope.tableState);
          }, 1000);
        })
        .catch(function () {
          console.log('error');
        });
    };
    $scope.currentStepTask = {id: ''};
    $scope.myTreeControl.scope.updatePageNumber = function (branch, page) {
      if (page > branch.page_number && branch.next) {
        branch.page_number = parseInt(branch.next.page);
        StateTree.getChildrenForStep(branch, branch.page_number).then(function (result) {
          branch = result;
        });
      } else if (page < branch.page_number && branch.prev && page > 0) {
        branch.page_number = parseInt(branch.prev.page);
        StateTree.getChildrenForStep(branch, branch.page_number).then(function (result) {
          branch = result;
        });
      }
    };
    $scope.myTreeControl.scope.mapStepStateProgress = $rootScope.mapStepStateProgress;

    //Click on +/- on step
    $scope.stepClick = function (step) {
      StateTree.getChildrenForStep(step);
    };

    $scope.getTask = function (branch) {
      $scope.stepTaskLoading = true;
      return Task.get({id: branch.id}).$promise.then(function (data) {
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

    $scope.getStep = function (branch) {
      $scope.stepTaskLoading = true;
      return Step.get({id: branch.id}).$promise.then(function (data) {
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
    //Click funciton for steps and tasks
    $scope.stepTaskClick = function (branch) {
      $scope.stepTaskLoading = true;
      if (branch.flow_type == 'task') {
        $scope.getTask(branch).then(function (data) {
          $scope.taskInfoModal();
        });
      } else {
        $scope.getStep(branch).then(function (data) {
          $scope.stepInfoModal();
        });
      }
    };

    $scope.checkPermission = function (permissionName) {
      return !angular.isUndefined(PermPermissionStore.getPermissionDefinition(permissionName));
    };
    $scope.extendedEqual = function (specification_data, model) {
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
    $scope.myTreeControl.scope.stateLoading = false;
    //Update status view data
    $scope.statusViewUpdate = function (tableState) {
      if (!angular.isUndefined(tableState)) {
        $scope.tableState = tableState;
        $scope.myTreeControl.scope.stateLoading = true;
        let expandedNodes = [];
        if ($scope.tree_data != []) {
          expandedNodes = checkExpanded($scope.tree_data);
        }

        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, $scope.tree_data);
        // if page Number is changed set newPage flag to reload tree_data instead of update
        if (paginationParams['pageNumber'] != $scope.paginationParams['pageNumber']) {
          $scope.newPage = true;
        } else {
          $scope.newPage = false;
        }
        $scope.paginationParams = angular.copy(paginationParams);
        // if andvanced filter "columnFilters" changed reset pagination to page 1
        if (JSON.stringify(vm.columnFilters) !== JSON.stringify($scope.columnFilters)) {
          paginationParams['pageNumber'] = 1;
          tableState.pagination['start'] = 0;
        }
        $scope.columnFilters = angular.copy(vm.columnFilters);
        return StateTree.getTreeData(
          $scope.ip,
          expandedNodes,
          paginationParams,
          sorting,
          search,
          vm.columnFilters
        ).then(function (value) {
          return $q.all(value).then(function (values) {
            if ($scope.tree_data.length && values.length && !$scope.newPage) {
              $scope.tree_data = updateStepProperties($scope.tree_data, values);
            } else {
              $scope.tree_data = value;
            }
            tableState.pagination.numberOfPages = Math.ceil(value.$httpHeaders('Count') / paginationParams.number); //set the number of pages so the pagination can update
            $scope.myTreeControl.scope.stateLoading = false;
            return value;
          });
        });
      }
    };

    // Calculates difference in two sets of steps and tasks recursively
    // and updates the old set with the differances.
    function updateStepProperties(A, B) {
      if (angular.isUndefined(A) || A.length > B.length) {
        A = B;
      }
      for (let i = 0; i < B.length; i++) {
        if (A[i]) {
          for (const prop in B[i]) {
            if (B[i].hasOwnProperty(prop) && prop != 'children') {
              A[i][prop] = compareAndReplace(A[i], B[i], prop);
            }
          }
          if (B[i].flow_type != 'task') {
            waitForChildren(A[i], B[i]).then(function (result) {
              result.step.children = result.children;
            });
          }
        } else {
          A.push(B[i]);
        }
      }
      return A;
    }

    // Waits for promises in b.children to resolve before returning
    // the result from updateStepProperties called with children of a and b
    function waitForChildren(a, b) {
      return $q.all(b.children).then(function (bchildren) {
        return {step: a, children: updateStepProperties(a.children, bchildren)};
      });
    }
    // If property in a and b does not have the same value, update a with the value of b
    function compareAndReplace(a, b, prop) {
      if (a.hasOwnProperty(prop) && b.hasOwnProperty(prop)) {
        if (a[prop] !== b[prop]) {
          a[prop] = b[prop];
        }
        return a[prop];
      } else {
        return b[prop];
      }
    }
    //checks expanded rows in tree structure
    function checkExpanded(nodes) {
      let ret = [];
      nodes.forEach(function (node) {
        if (node.expanded == true) {
          ret.push(node);
        }
        if (node.children && node.children.length > 0) {
          ret = ret.concat(checkExpanded(node.children));
        }
      });
      return ret;
    }

    //Creates and shows modal with task information
    $scope.taskInfoModal = function () {
      const modalInstance = $uibModal.open({
        animation: true,
        size: 'lg',
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/modals/task_info_modal.html',
        controller: 'TaskInfoModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            currentStepTask: $scope.currentStepTask,
          },
        },
      });
      modalInstance.result.then(
        function (data, $ctrl) {},
        function () {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    //Creates and shows modal with step information
    $scope.stepInfoModal = function () {
      const modalInstance = $uibModal.open({
        animation: true,
        size: 'lg',
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/modals/step_info_modal.html',
        controller: 'StepInfoModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            currentStepTask: $scope.currentStepTask,
          },
        },
      });
      modalInstance.result.then(
        function (data, $ctrl) {},
        function () {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
  }
}
