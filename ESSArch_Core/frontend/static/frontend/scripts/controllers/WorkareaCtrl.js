import * as Flow from '@flowjs/ng-flow/dist/ng-flow-standalone';

export default class WorkareaCtrl {
  constructor(
    vm,
    ipSortString,
    WorkareaFiles,
    Workarea,
    $scope,
    $controller,
    $rootScope,
    Resource,
    $interval,
    $timeout,
    appConfig,
    $cookies,
    $anchorScroll,
    $translate,
    $state,
    $http,
    listViewService,
    Requests,
    $uibModal,
    $sce,
    $window,
    ContextMenuBase,
    SelectedIPUpdater
  ) {
    $controller('BaseCtrl', {$scope: $scope, vm: vm, ipSortString: ipSortString, params: {}});

    vm.browserstate = {
      path: '',
    };
    vm.organizationMember = {
      current: null,
      options: [],
    };
    vm.$onInit = function() {
      $scope.redirectWithId();
      vm.organizationMember.current = $rootScope.auth;
      if ($scope.checkPermission('ip.see_all_in_workspaces') && $rootScope.auth.current_organization) {
        $http
          .get(appConfig.djangoUrl + 'organizations/' + $rootScope.auth.current_organization.id + '/')
          .then(function(response) {
            vm.organizationMember.options = response.data.group_members;
          });
      }
    };
    vm.archived = null;
    $scope.menuOptions = function(rowType, row) {
      return [
        ContextMenuBase.changeOrganization(function() {
          $scope.ip = row;
          $rootScope.ip = row;
          vm.changeOrganizationModal($scope.ip);
        }),
      ];
    };

    vm.callServer = function callServer(tableState) {
      $scope.ipLoading = true;
      if (vm.displayedIps.length == 0) {
        $scope.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        $scope.tableState = tableState;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        } else {
          tableState.search = {
            predicateObject: {
              $: vm.initialSearch,
            },
          };
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.itemsPerPage);
        Resource.getWorkareaIps(
          vm.workarea,
          paginationParams.start,
          paginationParams.number,
          paginationParams.pageNumber,
          tableState,
          sorting,
          search,
          $scope.expandedAics,
          $scope.columnFilters,
          vm.organizationMember.current
        )
          .then(function(result) {
            vm.displayedIps = result.data;
            tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
            $scope.ipLoading = false;
            $scope.initLoad = false;
            ipExists();
            SelectedIPUpdater.update(vm.displayedIps, $scope.ips, $scope.ip);
          })
          .catch(function(response) {
            if (response.status == 404) {
              const filters = angular.extend(
                {
                  state: ipSortString,
                },
                $scope.columnFilters
              );

              if (vm.workarea) {
                filters.workarea = vm.workarea;
              }

              listViewService.checkPages('workspace', paginationParams.number, filters).then(function(result) {
                tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
                tableState.pagination.start = result.numberOfPages * paginationParams.number - paginationParams.number;
                vm.callServer(tableState);
              });
            }
          });
      }
    };

    function ipExists() {
      if ($scope.ip != null) {
        let temp = false;
        vm.displayedIps.forEach(function(aic) {
          if ($scope.ip.id == aic.id) {
            temp = true;
          } else {
            aic.information_packages.forEach(function(ip) {
              if ($scope.ip.id == ip.id) {
                temp = true;
              }
            });
          }
        });
        if (!temp) {
          $scope.requestForm = false;
          $scope.eventlog = false;
          $scope.requestEventlog = false;
        }
      }
    }
    // Remove ip
    $scope.ipRemoved = function(ipObject) {
      $scope.edit = false;
      $scope.select = false;
      $scope.eventlog = false;
      $scope.requestForm = false;
      $scope.ips = [];
      $scope.ip = null;
      $rootScope.ip = null;
      if (vm.displayedIps.length == 0) {
        $state.reload();
      }
      $scope.getListViewData();
    };

    $scope.filebrowserClick = function(ip) {
      $scope.previousGridArrays = [];
      $scope.filebrowser = true;
      if (!$rootScope.flowObjects[$scope.ip.id]) {
        $scope.createNewFlow($scope.ip);
      }
      $scope.currentFlowObject = $rootScope.flowObjects[$scope.ip.id];
      if ($scope.filebrowser) {
        $scope.showFileUpload = false;
        $timeout(function() {
          $scope.showFileUpload = true;
        });
      }
      $scope.previousGridArrays = [];
    };

    $scope.removeIpModal = function(ipObject) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove-workarea-ip-modal.html',
        controller: 'ModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: function() {
            return {
              ip: ipObject,
              workarea: $state.includes('**.workarea.**'),
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $scope.ips = [];
          $scope.ip = null;
          $rootScope.ip = null;
          $scope.ipRemoved(ipObject);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    // **********************************
    //            Upload
    // **********************************

    vm.getUploadWorkareaType = function() {
      let type = null;
      for (let i = 0; i < $scope.ip.workarea.length; i++) {
        if (!$scope.ip.workarea[i].readOnly) {
          type = $scope.ip.workarea[i].type_name;
          break;
        }
      }
      return type;
    };

    $scope.updateGridArray = function(ip) {
      $scope.$broadcast('UPDATE_FILEBROWSER', {});
    };

    $scope.uploadDisabled = false;
    $scope.updateListViewTimeout = function(timeout) {
      $timeout(function() {
        $scope.getListViewData();
      }, timeout);
    };

    vm.flowDestination = null;
    $scope.showFileUpload = true;
    $scope.currentFlowObject = null;
    $scope.getFlowTarget = function() {
      return appConfig.djangoUrl + 'workarea-files/upload/?type=' + vm.getUploadWorkareaType() + '/';
    };
    $scope.getQuery = function(FlowFile, FlowChunk, isTest) {
      return {destination: vm.browserstate.path};
    };
    $scope.fileUploadSuccess = function(ip, file, message, flow) {
      $scope.uploadedFiles++;
      const path = flow.opts.query.destination + file.relativePath;

      WorkareaFiles.mergeChunks(
        {
          type: vm.getUploadWorkareaType(),
        },
        {path: path}
      );
    };
    $scope.fileTransferFilter = function(file) {
      return file.isUploading();
    };
    $scope.removeFiles = function() {
      $scope.selectedCards.forEach(function(file) {
        listViewService.deleteWorkareaFile(vm.workarea, vm.browserstate.path, file).then(function() {
          $scope.updateGridArray();
        });
      });
      $scope.selectedCards = [];
    };
    $scope.isSelected = function(card) {
      let cardClass = '';
      $scope.selectedCards.forEach(function(file) {
        if (card.name == file.name) {
          cardClass = 'card-selected';
        }
      });
      return cardClass;
    };
    $scope.resetUploadedFiles = function() {
      $scope.uploadedFiles = 0;
    };
    $scope.uploadedFiles = 0;
    $scope.flowCompleted = false;
    $scope.flowComplete = function(flow, transfers) {
      if (flow.progress() === 1) {
        flow.flowCompleted = true;
        flow.flowSize = flow.getSize();
        flow.flowFiles = transfers.length;
        flow.cancel();
        if (flow == $scope.currentFlowObject) {
          $scope.resetUploadedFiles();
        }
      }

      $scope.updateGridArray();
    };
    $scope.hideFlowCompleted = function(flow) {
      flow.flowCompleted = false;
    };
    $scope.getUploadedPercentage = function(totalSize, uploadedSize, totalFiles) {
      if (totalSize == 0 || uploadedSize / totalSize == 1) {
        return ($scope.uploadedFiles / totalFiles) * 100;
      } else {
        return (uploadedSize / totalSize) * 100;
      }
    };

    $scope.createNewFlow = function(ip) {
      const flowObj = new Flow({
        target: appConfig.djangoUrl + 'workarea-files/upload/?type=' + vm.getUploadWorkareaType(),
        chunkSize: 10 * 1024 * 1024, // 50MB
        simultaneousUploads: 15,
        maxChunkRetries: 5,
        chunkRetryInterval: 1000,
        headers: {'X-CSRFToken': $cookies.get('csrftoken')},
        complete: $scope.flowComplete,
      });
      flowObj.on('complete', function() {
        $scope.flowComplete(flowObj, flowObj.files);
      });
      flowObj.on('fileSuccess', function(file, message) {
        $scope.fileUploadSuccess(ip, file, message, flowObj);
      });
      flowObj.on('uploadStart', function() {
        flowObj.opts.query = {destination: vm.browserstate.path};
      });
      $rootScope.flowObjects[ip.id] = flowObj;
    };
  }
}
