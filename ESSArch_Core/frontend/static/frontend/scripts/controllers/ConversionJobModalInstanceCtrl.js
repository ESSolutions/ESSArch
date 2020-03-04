export default class ConversionJobModalInstanceCtrl {
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
    $ctrl.ips = [];
    $ctrl.model = {
      specification: {},
    };
    $ctrl.newSpec = {tool: null, path: null};
    $ctrl.tool = null;
    $ctrl.tools = [];
    $ctrl.toolData = {};
    $ctrl.toolDataForm = [];
    $ctrl.$onInit = () => {
      if (!data.remove) {
        if (!data.allow_close) {
          EditMode.enable();
        }
        if (data.job) {
          $ctrl.initModalLoad = true;
          $http
            .get(appConfig.djangoUrl + 'conversion-jobs/' + data.job.id + '/information-packages/')
            .then(response => {
              $ctrl.model = angular.copy(data.job);
              $ctrl.ips = response.data;
              $ctrl.initModalLoad = false;
            });
        } else {
          if (data.template) {
            $ctrl.model.specification = angular.copy(data.template).specification;
            if (data.template.specification && !angular.equals(data.template.specification, {})) {
              $ctrl.fullIpAppraisal = false;
            }
            if (data.template && !$ctrl.model.template) {
              $ctrl.model.template = data.template.id;
            }
          } else {
            $ctrl.model.template = null;
            $ctrl.model.specification = {};
          }
        }
      }
    };

    $ctrl.baseSpecFields = [
      {
        type: 'input',
        key: 'path',
        templateOptions: {
          label: $translate.instant('PATH'),
        },
      },
      {
        type: 'uiselect',
        key: 'tool',
        templateOptions: {
          options: function() {
            return $ctrl.tools;
          },
          valueProp: 'name',
          labelProp: 'name',
          onChange: newVal => {
            $ctrl.toolDataForm = $ctrl.tools.filter(x => x.name === newVal)[0].form;
          },
          placeholder: $translate.instant('ARCHIVE_MAINTENANCE.TOOL'),
          label: $translate.instant('ARCHIVE_MAINTENANCE.TOOL'),
          appendToBody: false,
          refresh: function(search) {
            if (angular.isUndefined(search) || search === null || search === '') {
              search = '';
            }
            return $ctrl.getTools(search).then(function() {
              this.options = $ctrl.tools;
              return $ctrl.tools;
            });
          },
        },
      },
    ];

    $ctrl.getTools = search => {
      return $http.get(appConfig.djangoUrl + 'conversion-tools/', {params: {search, pager: 'none'}}).then(response => {
        response.data.map(x => {
          return {name: x.name, fullItem: x};
        });
        $ctrl.tools = response.data;
        return response.data;
      });
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
        type: 'input',
        key: 'purpose',
        templateOptions: {
          label: $translate.instant('PURPOSE'),
          required: true,
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

    $ctrl.selectedAmongOthers = function(id) {
      let exists = false;
      $ctrl.ips.forEach(function(ip) {
        if (ip.id == id) {
          exists = true;
        }
      });
      return exists;
    };

    $ctrl.selectAll = () => {
      $ctrl.displayedIps.forEach(ip => {
        $ctrl.ips.push(ip);
      });
    };

    $ctrl.deselectAll = () => {
      $ctrl.ips = [];
    };

    $ctrl.addSpecification = function() {
      if ($ctrl.model.specification === null || $ctrl.model.specification === []) {
        $ctrl.model.specification = {};
      }
      if ($ctrl.newSpec.path) {
        $ctrl.model.specification[$ctrl.newSpec.path] = {
          tool: angular.copy($ctrl.newSpec.tool),
          options: angular.copy($ctrl.toolData),
        };
        $ctrl.newSpec = {
          path: '',
          tool: null,
        };
        $ctrl.toolData = {};
        $ctrl.toolDataForm = [];
      }
    };

    $ctrl.deleteSpecification = function(key) {
      delete $ctrl.model.specification[key];
    };

    $ctrl.removeTemplate = function(ip, template) {
      $ctrl.removingTemplate = true;
      $http({
        url: appConfig.djangoUrl + 'information-packages/' + ip.id + '/remove-conversion-template/',
        method: 'POST',
        data: {
          id: template.id,
        },
      })
        .then(function(response) {
          ip.templates.forEach(function(x, index, array) {
            if (x.id == template.id) {
              array.splice(index, 1);
            }
          });
          $ctrl.removingTemplate = false;
          $ctrl.showTemplatesTable(ip);
        })
        .catch(function(response) {
          $ctrl.removingTemplate = false;
        });
    };
    $ctrl.closeTemplatesTable = function() {
      $ctrl.conversionTemplates = [];
      $ctrl.ip = null;
    };

    $ctrl.runJob = function(job) {
      $http({
        url: appConfig.djangoUrl + 'conversion-jobs/' + job.id + '/run/',
        method: 'POST',
      }).then(() => {
        Notifications.add($translate.instant('ARCHIVE_MAINTENANCE.JOB_RUNNING'), 'success');
        $uibModalInstance.close();
      });
    };

    $ctrl.createJob = function(template) {
      $ctrl.creatingJob = true;
      $http({
        url: appConfig.djangoUrl + 'conversion-jobs/',
        method: 'POST',
        data: $ctrl.model,
      })
        .then(response => {
          return $http
            .post(appConfig.djangoUrl + 'conversion-jobs/' + response.data.id + '/information-packages/', {
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

    $ctrl.save = function(template) {
      $ctrl.creatingJob = true;
      $http({
        url: appConfig.djangoUrl + 'conversion-jobs/' + data.job.id + '/',
        method: 'PATCH',
        data: $ctrl.model,
      })
        .then(response => {
          return $http
            .post(appConfig.djangoUrl + 'conversion-jobs/' + response.data.id + '/information-packages/', {
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

    $ctrl.runningJob = false;
    $ctrl.createJobAndStart = function(template) {
      $ctrl.runningJob = true;
      $http({
        url: appConfig.djangoUrl + 'conversion-jobs/',
        method: 'POST',
        data: $ctrl.model,
      })
        .then(response => {
          return $http
            .post(appConfig.djangoUrl + 'conversion-jobs/' + response.data.id + '/information-packages/', {
              information_packages: $ctrl.ips.map(x => x.id),
            })
            .then(response => {
              return response;
            });
        })
        .then(response => {
          $http({
            url: appConfig.djangoUrl + 'conversion-jobs/' + response.data.id + '/run/',
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

    $ctrl.path = '';
    $ctrl.pathList = [];
    $ctrl.addPath = function(path) {
      if (path.length > 0) {
        $ctrl.pathList.push(path);
      }
    };
    $ctrl.removePath = function(path) {
      $ctrl.pathList.splice($ctrl.pathList.indexOf(path), 1);
    };
    $ctrl.conversionTemplate = null;

    $ctrl.remove = function() {
      $ctrl.removingJob = true;
      $http({
        url: appConfig.djangoUrl + 'conversion-jobs/' + data.job.id,
        method: 'DELETE',
      })
        .then(() => {
          $ctrl.removingJob = false;
          Notifications.add(
            $translate.instant('ARCHIVE_MAINTENANCE.CONVERSION_JOB_REMOVED', {name: data.job.label}),
            'success'
          );
          EditMode.disable();
          $uibModalInstance.close();
        })
        .catch(() => {
          $ctrl.removingJob = false;
        });
    };

    $ctrl.ok = function() {
      EditMode.disable();
      $uibModalInstance.close();
    };
    $ctrl.cancel = function() {
      EditMode.disable();
      $uibModalInstance.dismiss('cancel');
    };

    $ctrl.previewModal = function(job) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/preview_conversion_modal.html',
        controller: 'PreviewConversionJobModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'md',
        resolve: {
          data: {
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
        (data.allow_close === null || angular.isUndefined(data.allow_close) || data.allow_close !== true) &&
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
