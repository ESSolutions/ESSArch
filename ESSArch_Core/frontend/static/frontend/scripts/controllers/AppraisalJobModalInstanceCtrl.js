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
              $ctrl.ips = response.data;
              $ctrl.initModalLoad = false;
            });
        }
        if (data.template && !$ctrl.model.template) {
          $ctrl.model.template = data.template.id;
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
          {
            className: 'col-xs-12 col-sm-6 px-0 pl-md-base',
            type: 'datepicker',
            key: 'end_date',
            templateOptions: {
              label: $translate.instant('END_DATE'),
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
          Notifications.add($translate.instant('ARCHIVE_MAINTENANCE.JOB_CREATED'), 'success');
          EditMode.disable();
          $uibModalInstance.close($ctrl.data);
        })
        .catch(() => {
          $ctrl.creatingJob = false;
        });
    };

    $ctrl.createJob = () => {
      $ctrl.creatingJob = true;
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
        function(data, $ctrl) {},
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
