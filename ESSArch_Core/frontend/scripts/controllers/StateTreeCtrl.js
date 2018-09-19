angular.module('myApp').controller('StateTreeCtrl', function($scope, $translate, Step, Task, listViewService, appConfig, $timeout, $interval, PermPermissionStore, $q, $uibModal, $log, Notifications) {
    var vm = this;
    var stateInterval;
    $scope.myTreeControl = {};
    $scope.myTreeControl.scope = this;
    $scope.tree_data = [];
    $scope.angular = angular;
    $scope.statusShow = false;
    $scope.eventShow = false;
    vm.validations = [];

    vm.$onChanges = function() {
        $scope.ip = vm.ip;
        $scope.responsible = $translate.instant('RESPONSIBLE');
        $scope.label = $translate.instant('LABEL');
        $scope.date = $translate.instant('DATE');
        $scope.state = $translate.instant('STATE');
        $scope.status = $translate.instant('STATUS');
        $scope.expanding_property = {
            field: "label",
            displayName: $scope.label,
        };
        $scope.col_defs = [
            {
                field: "responsible",
                displayName: $scope.responsible
            },
            {
                cellTemplate: "<div ng-include src=\"'static/frontend/views/task_pagination.html'\"></div>"
            },
            {
                field: "time_started",
                displayName: $scope.date

            },
            {
                field: "status",
                displayName: $scope.state,
                cellTemplate: "<div ng-if=\"row.branch[col.field] == 'SUCCESS'\" class=\"step-state-success\"><b>{{'SUCCESS' | translate}}</b></div><div ng-if=\"row.branch[col.field] == 'FAILURE'\" class=\"step-state-failure\"><b>{{'FAILURE' | translate}}</b></div><div ng-if=\"row.branch[col.field] != 'SUCCESS' && row.branch[col.field] !='FAILURE'\" class=\"step-state-in-progress\"><b>{{'INPROGRESS' | translate}}</b></div>"

            },
            {
                field: "progress",
                displayName: $scope.status,
                cellTemplate: "<uib-progressbar class=\"progress\" value=\"row.branch[col.field]\" type=\"success\"><b>{{row.branch[col.field]+\"%\"}}</b></uib-progressbar>"
            }
        ];
        if($scope.checkPermission("WorkflowEngine.can_undo")) {
            $scope.col_defs.push({cellTemplate: "<div ng-include src=\"'workflow/undo.html'\"></div>"});
        }
        if($scope.checkPermission("WorkflowEngine.can_retry")) {
            $scope.col_defs.push({cellTemplate: "<div ng-include src=\"'workflow/redo.html'\"></div>"});
        }

        $scope.statusViewUpdate($scope.ip);
        $interval.cancel(stateInterval);
        stateInterval = $interval(function(){$scope.statusViewUpdate($scope.ip)}, appConfig.stateInterval);
    }

    vm.$onDestroy = function() {
        $interval.cancel(stateInterval);
    }

    //Cancel update intervals on state change
    $scope.$on('$stateChangeStart', function() {
        $interval.cancel(stateInterval);
    });

    // Key codes
    var arrowUp = 38;
    var arrowDown = 40;
    var escape = 27;
    var enter = 13;
    var space = 32;

    /**
     * Handle keydown events for state view table
     * @param {Event} e
     */
    $scope.myTreeControl.scope.stateTableKeydownListener = function(e, branch) {
        switch(e.keyCode) {
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
                $scope.stepTaskClick(branch)
                break;
            case space:
                e.preventDefault();
                if(branch.flow_type != "task") {
                    if(branch.expanded) {
                        branch.expanded = false;
                    } else {
                        branch.expanded = true;
                        $scope.statusViewUpdate($scope.ip);
                    }
                }
                break;
            case escape:
                e.preventDefault();
                if($scope.ip) {
                    closeContentViews();
                }
                document.getElementById("list-view").focus();
                break;
        }
    }

    //Undo step/task
    $scope.myTreeControl.scope.taskStepUndo = function(branch) {
        branch.$undo().then(function(response) {
            $timeout(function(){
                $scope.statusViewUpdate($scope.ip);
            }, 1000);
        }).catch(function() {
            console.log("error");
        });
    };
    //Redo step/task
    $scope.myTreeControl.scope.taskStepRedo = function(branch){
        branch.$retry().then(function(response) {
            $timeout(function(){
                $scope.statusViewUpdate($scope.ip);
            }, 1000);
        }).catch(function() {
            console.log("error");
        });
    };
    $scope.currentStepTask = {id: ""}
    $scope.myTreeControl.scope.updatePageNumber = function(branch, page) {
        if(page > branch.page_number && branch.next){
            branch.page_number = parseInt(branch.next.page);
            listViewService.getChildrenForStep(branch, branch.page_number).then(function(result) {
                branch = result;
            })
        } else if(page < branch.page_number && branch.prev && page > 0) {
            branch.page_number = parseInt(branch.prev.page);
            listViewService.getChildrenForStep(branch, branch.page_number).then(function(result) {
                branch = result;
            })
        }
    };

    //Click on +/- on step
    $scope.stepClick = function(step) {
        listViewService.getChildrenForStep(step);
    };

    $scope.getTask = function(branch) {
        $scope.stepTaskLoading = true;
        return Task.get({ id: branch.id }).$promise.then(function (data) {
            if(data.time_started !== null && data.time_done !== null) {
                var started = moment(data.time_started);
                var done = moment(data.time_done);
                data.duration = moment.utc(done.diff(started)).format('HH:mm:ss.SSS');
            } else {
                data.duration = null;
            }
            $scope.currentStepTask = data;
            $scope.stepTaskLoading = false;
            vm.getValidations(vm.validationTableState);
            return data;
        });
    }

    $scope.getStep = function(branch) {
        $scope.stepTaskLoading = true;
        return Step.get({ id: branch.id }).$promise.then(function (data) {
            if(data.time_started !== null && data.time_done !== null) {
                var started = moment(data.time_started);
                var done = moment(data.time_done);
                data.duration = moment.utc(done.diff(started)).format('HH:mm:ss.SSS');
            } else {
                data.duration = null;
            }
            $scope.currentStepTask = data;
            $scope.stepTaskLoading = false;
            return data;
        });
    }
    //Click funciton for steps and tasks
    $scope.stepTaskClick = function (branch) {
        $scope.stepTaskLoading = true;
        if (branch.flow_type == "task") {
            $scope.getTask(branch).then(function(data) {
                $scope.taskInfoModal();
            });
        } else {
            $scope.getStep(branch).then(function(data) {
                $scope.stepInfoModal();
            });
        }
    };

    // build comma separated args display string
    vm.getArgsString = function(args) {
        return args.map(function(x) {
            if(x === null) {
                return 'null';
            } else {
                return x;
            }
        }).join(', ');
    }

    $scope.checkPermission = function(permissionName) {
        return !angular.isUndefined(PermPermissionStore.getPermissionDefinition(permissionName));
    };
    $scope.extendedEqual = function(specification_data, model) {
        var returnValue = true;
        for(var prop in model) {
            if(model[prop] == "" && angular.isUndefined(specification_data[prop])){
                returnValue = false;
            }
        }
        if(returnValue) {
            return angular.equals(specification_data, model);
        } else {
            return true;
        }
    };
    $scope.myTreeControl.scope.stateLoading = false;
    //Update status view data
    $scope.statusViewUpdate = function (row) {
        $scope.myTreeControl.scope.stateLoading = true;
        var expandedNodes = [];
        if ($scope.tree_data != []) {
            expandedNodes = checkExpanded($scope.tree_data);
        }
        listViewService.getTreeData(row, expandedNodes).then(function (value) {
            $q.all(value).then(function (values) {
                if ($scope.tree_data.length) {
                    $scope.tree_data = updateStepProperties($scope.tree_data, values);
                } else {
                    $scope.tree_data = value;
                }
            })
        $scope.myTreeControl.scope.stateLoading = false;
        }, function (response) {
            if (response.status == 404) {
                $scope.statusShow = false;
                $timeout(function () {
                    $scope.getListViewData();
                    updateListViewConditional();
                }, 1000);
            }
        });
    };

    // Calculates difference in two sets of steps and tasks recursively
    // and updates the old set with the differances.
    function updateStepProperties(A, B) {
        if (A.length > B.length) {
            A.splice(0, B.length);
        }
        for (i = 0; i < B.length; i++) {
            if (A[i]) {
                for (var prop in B[i]) {
                    if (B[i].hasOwnProperty(prop) && prop != "children") {
                        A[i][prop] = compareAndReplace(A[i], B[i], prop);
                    }
                }
                if (B[i].flow_type != "task") {
                    waitForChildren(A[i], B[i]).then(function (result) {
                        result.step.children = result.children;
                    })
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
            return { step: a, children: updateStepProperties(a.children, bchildren) };
        })
    }
    // If property in a and b does not have the same value, update a with the value of b
    function compareAndReplace(a, b, prop) {
        if (a.hasOwnProperty(prop) && b.hasOwnProperty(prop)) {
            if (a[prop] !== b[prop]) {
                a[prop] = b[prop];
            }
            return a[prop];
        } else {
            return b[prop]
        }
    }
    //checks expanded rows in tree structure
    function checkExpanded(nodes) {
        var ret = [];
        nodes.forEach(function(node) {
            if(node.expanded == true) {
                ret.push(node);
            }
            if(node.children && node.children.length > 0) {
                ret = ret.concat(checkExpanded(node.children));
            }
        });
        return ret;
    }

    /**
     * Get validation list for task
     * @param {Object} task current task
     */
    vm.getValidations = function(tableState) {
        $scope.validationsLoading = true;
        if(vm.validations.length == 0) {
            $scope.initLoad = true;
        }
        if(!angular.isUndefined(tableState)) {
            vm.validationTableState = tableState;
            var search = "";
            if(tableState.search.predicateObject) {
                var search = tableState.search.predicateObject["$"];
            }
            var sorting = tableState.sort.reverse ? '-' : '' + tableState.sort.predicate;
            var pagination = tableState.pagination;
            var start = pagination.start || 0;     // This is NOT the page number, but the index of item in the list that you want to use to display the table.
            var number = pagination.number || vm.itemsPerPage;  // Number of entries showed per page.
            var pageNumber = start / number + 1;
            return Task.validations(
                {
                    id: $scope.currentStepTask.id,
                    page: pageNumber,
                    page_size: number,
                    ordering: sorting,
                    search: search
                })
                .$promise.then(function (resource) {
                    vm.validations = resource;
                    tableState.pagination.numberOfPages = Math.ceil(resource.$httpHeaders('Count') / number); //set the number of pages so the pagination can update
                    $scope.validationsLoading = false;
                    return resource;
                }).catch(function (response) {
                    if (response.data && response.data.detail) {
                        Notifications.add(response.data.detail, 'error')
                    } else if (response.status !== 500) {
                        Notifications.add('Could not get validations', 'error')
                    }
                    $scope.validationsLoading = false;
                    return response;
                })
        }
    }

    //Modal functions
    $scope.tracebackModal = function (profiles) {
        $scope.profileToSave = profiles;
        var modalInstance = $uibModal.open({
            animation: true,
            ariaLabelledBy: 'modal-title',
            ariaDescribedBy: 'modal-body',
            templateUrl: 'static/frontend/views/task_traceback_modal.html',
            scope: $scope,
            size: 'lg',
            controller: 'ModalInstanceCtrl',
            controllerAs: '$ctrl',
            resolve: {
                data: {}
            }
        })
        modalInstance.result.then(function (data) {
        }, function () {
            $log.info('modal-component dismissed at: ' + new Date());
        });
    }
    //Creates and shows modal with task information
    $scope.taskInfoModal = function () {
        var modalInstance = $uibModal.open({
            animation: true,
            size: 'lg',
            ariaLabelledBy: 'modal-title',
            ariaDescribedBy: 'modal-body',
            templateUrl: 'modals/task_info_modal.html',
            scope: $scope,
            controller: 'TaskInfoModalInstanceCtrl',
            controllerAs: '$ctrl',
            resolve: {
                data: {}
            }
        });
        modalInstance.result.then(function (data, $ctrl) {
        }, function () {
            $log.info('modal-component dismissed at: ' + new Date());
        });
    }
    //Creates and shows modal with step information
    $scope.stepInfoModal = function () {
        var modalInstance = $uibModal.open({
            animation: true,
            size: 'lg',
            ariaLabelledBy: 'modal-title',
            ariaDescribedBy: 'modal-body',
            templateUrl: 'modals/step_info_modal.html',
            scope: $scope,
            controller: 'StepInfoModalInstanceCtrl',
            controllerAs: '$ctrl',
            resolve: {
                data: {}
            }
        });
        modalInstance.result.then(function (data, $ctrl) {
        }, function () {
            $log.info('modal-component dismissed at: ' + new Date());
        });
    }
})
