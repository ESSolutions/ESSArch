export default class AppraisalJobModalInstanceCtrl {
  constructor(
    $translate,
    $uibModalInstance,
    appConfig,
    $http,
    data,
    Notifications,
    listViewService,
    $scope,
    EditMode,
    $uibModal,
    $log
  ) {
    const $ctrl = this;
    $ctrl.angular = angular;
    $ctrl.data = data;
    $ctrl.model = {};
    $ctrl.ips = [];
    $ctrl.fullIpAppraisal = true;

    $ctrl.initModalLoad = false;
    $ctrl.$onInit = () => {
      if (!data.remove) {
        EditMode.enable();

        if (data.job) {
          $ctrl.initModalLoad = true;
          $http
            .get(appConfig.djangoUrl + 'appraisal-jobs/' + data.job.id + '/information-packages/')
            .then(response => {
              $ctrl.model = angular.copy(data.job);
              if ($ctrl.model.package_file_pattern && $ctrl.model.package_file_pattern.length > 0) {
                $ctrl.fullIpAppraisal = false;
              }
              $ctrl.ips = response.data;
              $ctrl.initModalLoad = false;
            });
        } else {
          if (data.template) {
            $ctrl.model.package_file_pattern = angular.copy(data.template).package_file_pattern;
            if (data.template.package_file_pattern && data.template.package_file_pattern.length) {
              $ctrl.fullIpAppraisal = false;
            }
            if (data.template && !$ctrl.model.template) {
              $ctrl.model.template = data.template.id;
            }
          } else {
            $ctrl.model.template = null;
            $ctrl.model.package_file_pattern = [];
          }
        }
      }
    };

    $ctrl.fields = [
      {
        type: 'input',
        key: 'label',
        templateOptions: {
          label: $translate.instant('LABEL'),
        },
      },
      {
        className: 'row m-0',
        fieldGroup: [
          {
            className: 'col-xs-12 col-sm-6 px-0 pr-md-base',
            type: 'datepicker',
            key: 'start_date',
            templateOptions: {
              label: $translate.instant('START_DATE'),
              appendToBody: false,
            },
          },
        ],
      },
    ];

    $ctrl.path = '';
    $ctrl.addPath = function(path) {
      if (path.length > 0) {
        $ctrl.model.package_file_pattern.push(path);
      }
      $ctrl.path = '';
    };

    $ctrl.removePath = function(path) {
      $ctrl.model.package_file_pattern.splice($ctrl.model.package_file_pattern.indexOf(path), 1);
    };

    $ctrl.save = () => {
      if ($ctrl.fullIpAppraisal) {
        $ctrl.model.package_file_pattern = [];
      }
      $ctrl.creatingJob = true;
      $http({
        url: appConfig.djangoUrl + 'appraisal-jobs/' + $ctrl.model.id + '/',
        method: 'PATCH',
        data: $ctrl.model,
      })
        .then(response => {
          return $http
            .post(appConfig.djangoUrl + 'appraisal-jobs/' + response.data.id + '/information-packages/', {
              information_packages: $ctrl.ips.map(x => x.id),
            })
            .then(response => {
              return response;
            });
        })
        .then(() => {
          $ctrl.creatingJob = false;
          Notifications.add($translate.instant('ARCHIVE_MAINTENANCE.JOB_SAVED'), 'success');
          EditMode.disable();
          $uibModalInstance.close($ctrl.data);
        })
        .catch(() => {
          $ctrl.creatingJob = false;
        });
    };

    $ctrl.createJob = () => {
      $ctrl.creatingJob = true;
      if ($ctrl.fullIpAppraisal) {
        $ctrl.model.package_file_pattern = [];
      }
      $http({
        url: appConfig.djangoUrl + 'appraisal-jobs/',
        method: 'POST',
        data: $ctrl.model,
      })
        .then(response => {
          return $http
            .post(appConfig.djangoUrl + 'appraisal-jobs/' + response.data.id + '/information-packages/', {
              information_packages: $ctrl.ips.map(x => x.id),
            })
            .then(response => {
              return response;
            });
        })
        .then(() => {
          $ctrl.creatingJob = false;
          Notifications.add($translate.instant('ARCHIVE_MAINTENANCE.JOB_CREATED'), 'success');
          EditMode.disable();
          $uibModalInstance.close($ctrl.data);
        })
        .catch(() => {
          $ctrl.creatingJob = false;
        });
    };
    $ctrl.runningJob = false;
    $ctrl.createJobAndStart = () => {
      $ctrl.runningJob = true;
      if ($ctrl.fullIpAppraisal) {
        $ctrl.model.package_file_pattern = [];
      }
      $http({
        url: appConfig.djangoUrl + 'appraisal-jobs/',
        method: 'POST',
        data: $ctrl.model,
      })
        .then(response => {
          return $http
            .post(appConfig.djangoUrl + 'appraisal-jobs/' + response.data.id + '/information-packages/', {
              information_packages: $ctrl.ips.map(x => x.id),
            })
            .then(() => {
              return response;
            });
        })
        .then(response => {
          $http({
            url: appConfig.djangoUrl + 'appraisal-jobs/' + response.data.id + '/run/',
            method: 'POST',
          })
            .then(() => {
              $ctrl.runningJob = false;
              Notifications.add($translate.instant('ARCHIVE_MAINTENANCE.JOB_RUNNING'), 'success');
              EditMode.disable();
              $uibModalInstance.close($ctrl.data);
            })
            .catch(() => {
              $ctrl.runningJob = false;
            });
        })
        .catch(() => {
          $ctrl.runningJob = false;
        });
    };

    $ctrl.cancel = function() {
      EditMode.disable();
      $uibModalInstance.dismiss('cancel');
    };

    $ctrl.ipTableClick = (row, event) => {
      if ($ctrl.selectedAmongOthers(row.id)) {
        $ctrl.ips.forEach((x, idx, array) => {
          if (x.id === row.id) {
            array.splice(idx, 1);
          }
        });
      } else {
        $ctrl.ips.push(row);
      }
    };

    $ctrl.selectAll = () => {
      $ctrl.displayedIps.forEach(ip => {
        $ctrl.ips.push(ip);
      });
    };

    $ctrl.deselectAll = () => {
      $ctrl.ips = [];
    };

    $ctrl.selectedAmongOthers = function(id) {
      let exists = false;
      $ctrl.ips.forEach(function(ip) {
        if (ip.id == id) {
          exists = true;
        }
      });
      return exists;
    };

    $ctrl.getIps = () => {
      $ctrl.callServer($ctrl.tableState);
    };

    $ctrl.displayedIps = [];
    $ctrl.callServer = function(tableState) {
      $ctrl.ipLoading = true;
      if ($ctrl.displayedIps.length == 0) {
        $ctrl.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        $ctrl.tableState = tableState;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        let ordering = tableState.sort.predicate;
        if (tableState.sort.reverse) {
          ordering = '-' + ordering;
        }

        const paginationParams = listViewService.getPaginationParams(tableState.pagination, $ctrl.itemsPerPage);
        $http({
          method: 'GET',
          url: appConfig.djangoUrl + 'information-packages/',
          params: angular.extend(
            {
              search,
              ordering,
              view_type: 'flat',
              active: true,
              page: paginationParams.pageNumber,
              page_size: paginationParams.number,
              pager: paginationParams.pager,
              archived: true,
            },
            $ctrl.columnFilters
          ),
        })
          .then(function(response) {
            $ctrl.displayedIps = response.data;
            tableState.pagination.numberOfPages = Math.ceil(response.headers('Count') / paginationParams.number); //set the number of pages so the pagination can update
            $ctrl.ipLoading = false;
            $ctrl.initLoad = false;
            ipExists();
            SelectedIPUpdater.update($ctrl.displayedIps, $ctrl.ips, $ctrl.ip);
          })
          .catch(function(response) {
            if (response.status == 404) {
              const filters = angular.extend(
                {
                  state: ipSortString,
                },
                $ctrl.columnFilters
              );

              if ($ctrl.workarea) {
                filters.workarea = $ctrl.workarea;
              }

              listViewService.checkPages('ip', paginationParams.number, filters).then(function(response) {
                tableState.pagination.numberOfPages = response.numberOfPages; //set the number of pages so the pagination can update
                tableState.pagination.start =
                  response.numberOfPages * paginationParams.number - paginationParams.number;
                $ctrl.callServer(tableState);
              });
            }
          });
      }
    };

    $ctrl.tagsPipe = function(tableState) {
      $ctrl.tagsLoading = true;
      if (angular.isUndefined($ctrl.tags) || $ctrl.tags.length == 0) {
        $scope.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        $ctrl.tagsTableState = tableState;
        var search = '';
        if (tableState.search.predicateObject) {
          var search = tableState.search.predicateObject['$'];
        }
        const sorting = tableState.sort;
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, $ctrl.itemsPerPage);

        let sortString = sorting.predicate;
        if (sorting.reverse) {
          sortString = '-' + sortString;
        }

        $ctrl
          .getTags(data.job, {
            page: paginationParams.pageNumber,
            page_size: paginationParams.number,
            pager: paginationParams.pager,
            ordering: sortString,
            search: search,
          })
          .then(function(response) {
            tableState.pagination.numberOfPages = Math.ceil(response.headers('Count') / paginationParams.number); //set the number of pages so the pagination can update
            $scope.initLoad = false;
            $ctrl.tagsLoading = false;
            response.data.forEach(function(x) {
              if (angular.isUndefined(x.id) && x._id) {
                x.id = x._id;
              }
            });
            $ctrl.tags = response.data;
          });
      }
    };

    $ctrl.getTags = function(job, params) {
      return $http
        .get(appConfig.djangoUrl + 'appraisal-jobs/' + job.id + '/tags/', {params: params})
        .then(function(response) {
          return response;
        });
    };

    $ctrl.remove = () => {
      $ctrl.removingJob = true;
      $http
        .delete(appConfig.djangoUrl + 'appraisal-jobs/' + data.job.id + '/')
        .then(() => {
          $ctrl.removingJob = false;
          EditMode.disable();
          $uibModalInstance.close();
        })
        .catch(() => {
          $ctrl.removingJob = false;
        });
    };

    $ctrl.runJob = function(job) {
      $http({
        url: appConfig.djangoUrl + 'appraisal-jobs/' + job.id + '/run/',
        method: 'POST',
      }).then(() => {
        Notifications.add($translate.instant('ARCHIVE_MAINTENANCE.JOB_RUNNING'), 'success');
        $uibModalInstance.close();
      });
    };

    $ctrl.removeNodeModal = function(node) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove_node_from_appraisal_job_modal.html',
        controller: 'NodeAppraisalJobModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            job: data.job,
            remove: true,
            node,
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $ctrl.tagsPipe($ctrl.tagsTableState);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    $ctrl.previewModal = function(job) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/preview_appraisal_modal.html',
        controller: 'AppraisalModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            preview: true,
            job,
          },
        },
      });
      modalInstance.result.then(
        function(data) {},
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    $scope.$on('modal.closing', function(event, reason, closed) {
      if (
        (data.allow_close === null || angular.isUndefined(data.remove) || data.remove !== true) &&
        (reason === 'cancel' || reason === 'backdrop click' || reason === 'escape key press')
      ) {
        const message = $translate.instant('UNSAVED_DATA_WARNING');
        if (!confirm(message)) {
          event.preventDefault();
        } else {
          EditMode.disable();
        }
      }
    });
  }
}
