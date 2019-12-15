/*
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2019 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
*/

export default class BaseCtrl {
  constructor(
    vm,
    ipSortString,
    params,
    $log,
    $uibModal,
    $timeout,
    $scope,
    $window,
    $http,
    appConfig,
    $state,
    $rootScope,
    listViewService,
    $interval,
    Resource,
    $translate,
    $cookies,
    PermPermissionStore,
    Requests,
    ContentTabs,
    SelectedIPUpdater,
    $transitions,
    $stateParams,
    $q,
    Filters
  ) {
    // Initialize variables

    $scope.$window = $window;
    $scope.$state = $state;
    vm.options = {};
    $scope.max = 100;
    $scope.stepTaskInfoShow = false;
    $scope.statusShow = false;
    $scope.eventShow = false;
    $scope.select = false;
    $scope.subSelect = false;
    $scope.edit = false;
    $scope.eventlog = false;
    $scope.requestForm = false;
    $scope.filebrowser = false;
    $scope.ip = null;
    $rootScope.ip = null;
    $scope.ips = [];
    $scope.myTreeControl = {};
    $scope.myTreeControl.scope = this;
    vm.itemsPerPage = $cookies.get('essarch-ips-per-page') || 10;
    vm.archived = false;
    vm.specificTabs = [];
    vm.columnFilters = {};
    vm.fields = [];

    $scope.$translate = $translate;

    $scope.ContentTabs = ContentTabs;
    // Can be overwritten in controllers to change title
    vm.listViewTitle = $translate.instant('INFORMATION_PACKAGES');
    vm.initialSearch = null;
    const watchers = [];
    // Init request form

    const docStateMap = {
      prepareIp: 'producer/prepare-ip.html',
      collectContent: 'producer/collect-content.html',
      createSip: 'producer/create-sip.html',
      submitSip: 'producer/submit-sip.html',
      reception: 'ingest/reception.html',
      ipApproval: 'ingest/approval.html',
      accessIp: 'access/storage-units.html',
      workarea: 'workspace/workspace.html',
      createDip: 'access/dissemination.html',
    };
    vm.getStateDocPage = function() {
      const page = $state.current.name.split('.').pop();
      return docStateMap[page];
    };

    //Request form data
    $scope.initRequestData = function() {
      vm.request = {
        type: '',
        purpose: '',
        storageMedium: {
          value: '',
          options: ['Disk', 'Tape(type1)', 'Tape(type2)'],
          appraisal_date: null,
        },
      };
    };
    $scope.initRequestData();

    $scope.redirectWithId = () => {
      if ($stateParams.id) {
        let promise;
        if ($state.is('home.access.orders')) {
          promise = $http.get(appConfig.djangoUrl + 'orders/' + $stateParams.id + '/').then(response => {
            return response.data;
          });
        } else if ($state.is('home.workarea')) {
          promise = $http.get(appConfig.djangoUrl + 'workareas/' + $stateParams.id + '/').then(response => {
            return response.data;
          });
        } else if ($state.is('home.ingest.reception')) {
          promise = $http.get(appConfig.djangoUrl + 'ip-reception/' + $stateParams.id + '/').then(response => {
            return response.data;
          });
        } else {
          promise = listViewService.getIp($stateParams.id).then(ip => {
            if (
              ipSortString.includes(ip.state) ||
              ($state.includes('home.access.createDip') && ip.package_type === 4)
            ) {
              return ip;
            } else {
              return $q.reject('Not valid page');
            }
          });
        }
        promise
          .then(ip => {
            vm.initialSearch = angular.copy($stateParams.id);
            $scope.ipTableClick(ip, {}, {noStateChange: true});

            $timeout(() => {
              $scope.getListViewData();
            });
          })
          .catch(() => {
            $state.go($state.current.name, {id: null});
          });
      } else {
      }
    };

    vm.$onInit = () => {
      $scope.redirectWithId();
    };

    watchers.push(
      $scope.$watch(
        function() {
          return $scope.ips.length;
        },
        function(newVal) {
          $timeout(function() {
            if ($scope.ip !== null) {
              vm.specificTabs = ContentTabs.visible([$scope.ip], $state.current.name);
            } else {
              vm.specificTabs = ContentTabs.visible($scope.ips, $state.current.name);
            }
            if (newVal > 0) {
              vm.activeTab = vm.specificTabs[0];
            } else {
              vm.activeTab = 'no_tabs';
            }
          });
        },
        true
      )
    );

    watchers.push(
      $scope.$watch(
        function() {
          return $scope.ip;
        },
        function(newVal) {
          if (newVal !== null) {
            $timeout(function() {
              vm.specificTabs = ContentTabs.visible([$scope.ip], $state.current.name);
              if (vm.specificTabs.length > 0) {
                vm.activeTab = vm.specificTabs[0];
              } else {
                vm.activeTab = 'tasks';
              }
            });
          }
        },
        true
      )
    );

    // Initialize intervals

    //Cancel update intervals on state change
    watchers.push(
      $transitions.onSuccess({}, function($transition) {
        if ($transition.from().name !== $transition.to().name) {
          $interval.cancel(listViewInterval);
          watchers.forEach(function(watcher) {
            watcher();
          });
        } else {
          let params = $transition.params();
          if (params.id !== null && ($scope.ip === null || params.id !== $scope.ip.id)) {
            $scope.redirectWithId();
          } else if (params.id === null && $scope.ip !== null) {
            $scope.ipTableClick($scope.ip);
          }
        }
      })
    );

    $scope.$on('REFRESH_LIST_VIEW', function(event, data) {
      $scope.getListViewData();
    });

    // list view update interval

    //Update ip list view with an interval
    //Update only if status < 100 and no step has failed in any IP
    let listViewInterval;
    vm.updateListViewConditional = function() {
      $interval.cancel(listViewInterval);
      listViewInterval = $interval(function() {
        let updateVar = false;
        vm.displayedIps.forEach(function(ip, idx) {
          if (ip.status < 100) {
            if (ip.step_state != 'FAILURE') {
              updateVar = true;
            }
          }
        });
        if (updateVar) {
          $scope.getListViewData();
        } else {
          $interval.cancel(listViewInterval);
          listViewInterval = $interval(function() {
            let updateVar = false;
            vm.displayedIps.forEach(function(ip, idx) {
              if (ip.status < 100) {
                if (ip.step_state != 'FAILURE') {
                  updateVar = true;
                }
              }
            });
            if (!updateVar) {
              $scope.getListViewData();
            } else {
              vm.updateListViewConditional();
            }
          }, appConfig.ipIdleInterval);
        }
      }, appConfig.ipInterval);
    };
    vm.updateListViewConditional();

    // Click fucntions

    // List view

    vm.displayedIps = [];
    //Get data according to ip table settings and populates ip table
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
        if (ipSortString.indexOf('Deleting') === -1) {
          ipSortString.push('Deleting'); // Add deleting if not already exists
        }
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.itemsPerPage);
        Resource.getIpPage(
          paginationParams,
          params,
          sorting,
          search,
          ipSortString,
          $scope.expandedAics,
          vm.columnFilters,
          vm.archived,
          vm.workarea
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
                vm.columnFilters
              );

              if (vm.workarea) {
                filters.workarea = vm.workarea;
              }

              listViewService.checkPages('ip', paginationParams.number, filters).then(function(result) {
                tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
                tableState.pagination.start = result.numberOfPages * paginationParams.number - paginationParams.number;
                vm.callServer(tableState);
              });
            }
          });
      }
    };

    vm.sa_locked = function() {
      if ($scope.ip !== null && $scope.ips.length == 0) {
        return $scope.ip.submission_agreement_locked;
      } else {
        let allLocked = true;
        $scope.ips.forEach(function(ip) {
          if (!ip.submission_agreement_locked) {
            allLocked = false;
          }
        });
        return allLocked;
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
          $scope.eventShow = false;
          $scope.statusShow = false;
          $scope.filebrowser = false;
          $scope.requestForm = false;
          $scope.eventlog = false;
          $scope.requestEventlog = false;
        }
      }
    }

    //Get data for list view
    $scope.getListViewData = function() {
      vm.callServer($scope.tableState);
      $rootScope.$broadcast('load_tags', {});
    };

    // Keyboard shortcuts
    function selectNextIp() {
      let index = 0;
      let inChildren = false;
      let parent = null;
      if ($scope.ip) {
        vm.displayedIps.forEach(function(ip, idx, array) {
          if ($scope.ip.id === ip.id) {
            index = idx + 1;
          }
          if (ip.information_packages) {
            if (ip.collapsed == false && $scope.ip.id === ip.id) {
              inChildren = true;
              parent = ip;
              index = 0;
            }
            ip.information_packages.forEach(function(child, i, arr) {
              if ($scope.ip.id === child.id) {
                if (i == arr.length - 1) {
                  index = idx + 1;
                } else {
                  index = i + 1;
                  parent = ip;
                  inChildren = true;
                }
              }
            });
          }
        });
      }
      if (inChildren) {
        $scope.ipTableClick(parent.information_packages[index]);
      } else if (index !== vm.displayedIps.length) {
        $scope.ipTableClick(vm.displayedIps[index]);
      }
    }

    function previousIp() {
      let index = vm.displayedIps.length - 1;
      let parent = null;
      if ($scope.ip) {
        vm.displayedIps.forEach(function(ip, idx, array) {
          if ($scope.ip.id === ip.id) {
            index = idx - 1;
          }
          if (ip.information_packages) {
            if (idx > 0 && array[idx - 1].collapsed == false && $scope.ip.id === ip.id) {
              parent = array[idx - 1];
              index = parent.information_packages.length - 1;
            } else {
              ip.information_packages.forEach(function(child, i, arr) {
                if ($scope.ip.id === child.id) {
                  if (i === 0) {
                    index = idx;
                  } else {
                    index = i - 1;
                    parent = ip;
                  }
                }
              });
            }
          }
        });
      }
      if (parent != null) {
        $scope.ipTableClick(parent.information_packages[index]);
      } else if (index >= 0) {
        $scope.ipTableClick(vm.displayedIps[index]);
      }
    }

    function closeContentViews() {
      $scope.stepTaskInfoShow = false;
      $scope.statusShow = false;
      $scope.eventShow = false;
      $scope.select = false;
      $scope.subSelect = false;
      $scope.edit = false;
      $scope.eventlog = false;
      $scope.filebrowser = false;
      $scope.requestForm = false;
      $scope.initRequestData();
      $scope.ip = null;
      $rootScope.ip = null;
    }
    const arrowLeft = 37;
    const arrowUp = 38;
    const arrowRight = 39;
    const arrowDown = 40;
    const escape = 27;
    const enter = 13;
    const space = 32;

    /**
     * Handle keydown events in list view
     * @param {Event} e
     */
    vm.ipListKeydownListener = function(e) {
      switch (e.keyCode) {
        case arrowDown:
          e.preventDefault();
          selectNextIp();
          break;
        case arrowUp:
          e.preventDefault();
          previousIp();
          break;
        case arrowLeft:
          e.preventDefault();
          var pagination = $scope.tableState.pagination;
          if (pagination.start != 0) {
            pagination.start -= pagination.number;
            $scope.getListViewData();
          }
          break;
        case arrowRight:
          e.preventDefault();
          var pagination = $scope.tableState.pagination;
          if (pagination.start / pagination.number + 1 < pagination.numberOfPages) {
            pagination.start += pagination.number;
            $scope.getListViewData();
          }
          break;
        case space:
          e.preventDefault();
          if ($state.is('home.ingest.reception')) {
            $scope.includeIp($scope.ip);
            $scope.getListViewData();
          } else {
            $scope.expandAic($scope.ip);
          }
          break;
        case escape:
          if ($scope.ip) {
            closeContentViews();
          }
          break;
      }
    };

    /**
     * Handle keydown events in views outside list view
     * @param {Event} e
     */
    vm.contentViewsKeydownListener = function(e) {
      switch (e.keyCode) {
        case escape:
          if ($scope.ip) {
            closeContentViews();
          }
          document.getElementById('list-view').focus();
          break;
      }
    };

    // Validators

    vm.validatorModel = {};
    vm.validatorFields = [
      {
        templateOptions: {
          label: $translate.instant('VALIDATEFILEFORMAT'),
        },
        defaultValue: true,
        type: 'checkbox',
        ngModelElAttrs: {
          tabindex: '-1',
        },
        key: 'validate_file_format',
      },
      {
        templateOptions: {
          label: $translate.instant('VALIDATEXMLFILE'),
        },
        defaultValue: true,
        type: 'checkbox',
        ngModelElAttrs: {
          tabindex: '-1',
        },
        key: 'validate_xml_file',
      },
      {
        templateOptions: {
          label: $translate.instant('VALIDATELOGICALPHYSICALREPRESENTATION'),
        },
        defaultValue: true,
        type: 'checkbox',
        ngModelElAttrs: {
          tabindex: '-1',
        },
        key: 'validate_logical_physical_representation',
      },
      {
        templateOptions: {
          label: $translate.instant('VALIDATEINTEGRITY'),
        },
        defaultValue: true,
        type: 'checkbox',
        ngModelElAttrs: {
          tabindex: '-1',
        },
        key: 'validate_integrity',
      },
    ];

    // File conversion

    vm.fileConversionModel = {};
    $translate(['YES', 'NO']).then(function(translations) {
      vm.fileConversionFields = [
        {
          templateOptions: {
            type: 'text',
            label: $translate.instant('CONVERTFILES'),
            options: [
              {name: translations.YES, value: true},
              {name: translations.NO, value: false},
            ],
          },
          defaultValue: false,
          type: 'select',
          ngModelElAttrs: {
            tabindex: '-1',
          },
          key: 'file_conversion',
        },
      ];
    });

    // Requests
    $scope.submitRequest = function(ip, request) {
      switch (request.type) {
        case 'preserve':
          if ($scope.ips.length > 0) {
            vm.preserveModal($scope.ips, request);
          } else {
            vm.preserveModal(ip, request);
          }
          break;
        case 'get':
          if ($scope.ips.length > 0) {
            vm.accessModal($scope.ips, request);
          } else {
            vm.accessModal(ip, request);
          }
          break;
        case 'get_tar':
          if ($scope.ips.length > 0) {
            vm.accessModal($scope.ips, request);
          } else {
            vm.accessModal(ip, request);
          }
          break;
        case 'get_as_new':
          if ($scope.ips.length > 0) {
            vm.accessModal($scope.ips, request);
          } else {
            vm.accessModal(ip, request);
          }
          break;
        case 'move_to_approval':
          if ($scope.ips.length > 0) {
            vm.moveToApprovalModal($scope.ips, request);
          } else {
            vm.moveToApprovalModal(ip, request);
          }
          break;
        case 'download_dip':
          vm.downloadDipModal(ip);
          break;
        case 'download_order':
          vm.downloadOrderModal(ip);
          break;
        case 'diff_check':
          console.log('request not implemented');
          break;
        default:
          console.log('request not matched');
          break;
      }
    };

    vm.preserveModal = function(ip, request) {
      let ips = null;
      if (Array.isArray(ip)) {
        ips = ip;
      }
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/preserve_modal.html',
        controller: 'PreserveModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: function() {
            return {
              ip: ip,
              ips: ips,
              request: request,
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $scope.ip = null;
          $rootScope.ip = null;
          $scope.ips = [];
          $scope.initRequestData();
          $scope.getListViewData();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.accessModal = function(ip, request) {
      let ips = null;
      if (Array.isArray(ip)) {
        ips = ip;
      }
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/access_modal.html',
        controller: 'AccessModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: function() {
            return {
              ip: ip,
              ips: ips,
              request: request,
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $scope.ip = null;
          $rootScope.ip = null;
          $scope.ips = [];
          $scope.initRequestData();
          $timeout(function() {
            $scope.getListViewData();
          });
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    vm.moveToApprovalModal = function(ip, request) {
      let ips = null;
      if (Array.isArray(ip)) {
        ips = ip;
      }
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/move_to_approval_modal.html',
        controller: 'MoveToApprovalModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: function() {
            return {
              ip: ip,
              ips: ips,
              request: request,
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $scope.ip = null;
          $scope.ips = [];
          $rootScope.ip = null;
          $scope.initRequestData();
          $timeout(function() {
            vm.submittingRequest = false;
            $scope.getListViewData();
          });
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    // Preserve IP
    $scope.preserveIp = function(ip, request) {
      vm.submittingRequest = true;
      const params = {purpose: request.purpose};
      params.policy =
        request.archivePolicy && request.archivePolicy.value != '' ? request.archivePolicy.value.id : null;
      if (request.appraisal_date != null) {
        params.appraisal_date = request.appraisal_date;
      }
      Requests.preserve(ip, params).then(function(result) {
        $scope.requestForm = false;
        $scope.eventlog = false;
        $scope.requestEventlog = false;
        $scope.filebrowser = false;
        $scope.eventShow = false;
        $scope.statusShow = false;
        vm.submittingRequest = false;
        $scope.initRequestData();
        $scope.getListViewData();
      });
    };

    $scope.accessIp = function(ip, request) {
      vm.submittingRequest = true;
      const data = {
        purpose: request.purpose,
        tar: request.type === 'get_tar',
        extracted: request.type === 'get',
        new: request.type === 'get_as_new',
        package_xml: request.package_xml,
        aic_xml: request.aic_xml,
      };
      Requests.access(ip, data).then(function(response) {
        $scope.requestForm = false;
        $scope.eventlog = false;
        $scope.requestEventlog = false;
        $scope.filebrowser = false;
        $scope.edit = false;
        $scope.select = false;
        $scope.eventShow = false;
        $scope.statusShow = false;
        vm.submittingRequest = false;
        $scope.initRequestData();
        $timeout(function() {
          $scope.ip = null;
          $rootScope.ip = null;
          $scope.getListViewData();
        });
      });
    };

    $scope.moveToApproval = function(ip, request) {
      vm.submittingRequest = true;
      const data = {purpose: request.purpose};
      Requests.moveToApproval(ip, data).then(function(response) {
        $scope.requestForm = false;
        $scope.eventlog = false;
        $scope.requestEventlog = false;
        $scope.eventShow = false;
        $scope.filebrowser = false;
        $scope.edit = false;
        $scope.select = false;
        $scope.eventShow = false;
        $scope.statusShow = false;
        $scope.initRequestData();
        $timeout(function() {
          vm.submittingRequest = false;
          $scope.ip = null;
          $rootScope.ip = null;
          $scope.getListViewData();
        });
      });
    };

    // Click functionality

    //Click function for Ip table
    $scope.ipTableClick = function(row, event, options) {
      if (event && event.shiftKey) {
        vm.shiftClickrow(row);
      } else if (event && event.ctrlKey) {
        vm.ctrlClickRow(row);
      } else {
        vm.selectSingleRow(row, options);
        if (row.information_packages && row.information_packages.length > 0) {
          $scope.expandAic(row);
        }
      }
    };

    vm.shiftClickrow = function(row) {
      const index = vm.displayedIps
        .map(function(ip) {
          return ip.id;
        })
        .indexOf(row.id);
      let last;
      if ($scope.ips.length > 0) {
        last = $scope.ips[$scope.ips.length - 1].id;
      } else if ($scope.ips.length <= 0 && $scope.ip != null) {
        last = $scope.ip.id;
      } else {
        last = null;
      }
      const lastIndex =
        last != null
          ? vm.displayedIps
              .map(function(ip) {
                return ip.id;
              })
              .indexOf(last)
          : index;
      if (lastIndex > index) {
        for (let i = lastIndex; i >= index; i--) {
          if (!$scope.selectedAmongOthers(vm.displayedIps[i].id)) {
            $scope.ips.push(vm.displayedIps[i]);
          }
        }
      } else if (lastIndex < index) {
        for (let i = lastIndex; i <= index; i++) {
          if (!$scope.selectedAmongOthers(vm.displayedIps[i].id)) {
            $scope.ips.push(vm.displayedIps[i]);
          }
        }
      } else {
        vm.selectSingleRow(row);
      }
      $scope.statusShow = false;
    };

    vm.ctrlClickRow = function(row) {
      if (row.package_type != 1) {
        if ($scope.ip != null) {
          $scope.ips.push($scope.ip);
        }
        $scope.ip = null;
        $rootScope.ip = null;
        $scope.eventShow = false;
        $scope.statusShow = false;
        $scope.filebrowser = false;
        let deleted = false;
        $scope.ips.forEach(function(ip, idx, array) {
          if (!deleted && ip.object_identifier_value == row.object_identifier_value) {
            array.splice(idx, 1);
            deleted = true;
          }
        });
        if (!deleted) {
          if ($scope.ips.length == 0) {
            $scope.initRequestData();
          }
          $scope.select = true;
          $scope.eventlog = true;
          $scope.edit = true;
          $scope.requestForm = true;
          $scope.eventShow = false;
          $scope.ips.push(row);
        }
        if ($scope.ips.length == 1) {
          $scope.ip = $scope.ips[0];
          $rootScope.ip = $scope.ips[0];
          $scope.ips = [];
        }
      }
      $scope.statusShow = false;
    };

    vm.selectSingleRow = function(row, options) {
      if (row.package_type == 1) {
        $scope.select = false;
        $scope.eventlog = false;
        $scope.edit = false;
        $scope.eventShow = false;
        $scope.requestForm = false;
        if ($scope.ip != null && $scope.ip.object_identifier_value == row.object_identifier_value) {
          $scope.ip = null;
          $rootScope.ip = null;
          $scope.filebrowser = false;
          if (angular.isUndefined(options) || !options.noStateChange) {
            $state.go($state.current.name, {id: null});
          }
        } else {
          $scope.ip = null;
          $rootScope.ip = null;
          vm.activeTab = null;
          $timeout(() => {
            $scope.ip = row;
            $rootScope.ip = $scope.ip;
            if (angular.isUndefined(options) || !options.noStateChange) {
              $state.go($state.current.name, {id: row.id});
            }
          });
        }
        return;
      }
      $scope.ips = [];
      if ($scope.select && $scope.ip != null && $scope.ip.object_identifier_value == row.object_identifier_value) {
        $scope.select = false;
        $scope.eventlog = false;
        $scope.edit = false;
        $scope.eventShow = false;
        $scope.requestForm = false;
        $scope.ip = null;
        $rootScope.ip = null;
        $scope.filebrowser = false;
        $scope.initRequestData();
        if (angular.isUndefined(options) || !options.noStateChange) {
          $state.go($state.current.name, {id: null});
        }
      } else {
        $scope.select = true;
        $scope.eventlog = true;
        $scope.edit = true;
        $scope.requestForm = true;
        $scope.eventShow = false;
        $scope.ip = null;
        $rootScope.ip = null;
        vm.activeTab = null;
        $timeout(() => {
          $scope.ip = row;
          $rootScope.ip = $scope.ip;
          if (angular.isUndefined(options) || !options.noStateChange) {
            $state.go($state.current.name, {id: row.id});
          }
        });
      }
      $scope.statusShow = false;
    };

    $scope.selectedAmongOthers = function(id) {
      let exists = false;
      $scope.ips.forEach(function(ip) {
        if (ip.id == id) {
          exists = true;
        }
      });
      return exists;
    };

    vm.selectAll = function() {
      $scope.ips = [];
      vm.displayedIps.forEach(function(ip) {
        vm.ctrlClickRow(ip);
        if (ip.information_packages && ip.information_packages.length > 0 && !ip.collapsed) {
          ip.information_packages.forEach(function(subIp) {
            vm.ctrlClickRow(subIp);
          });
        }
      });
    };
    vm.deselectAll = function() {
      $scope.ips = [];
      $scope.ip = null;
      $rootScope.ip = null;
    };

    // Basic functions

    //Adds a new event to the database
    $scope.addEvent = function(ip, eventType, eventDetail) {
      listViewService.addEvent(ip, eventType, eventDetail).then(function(value) {});
    };

    //Functions for extended filters
    $scope.searchDisabled = function() {
      if ($scope.filterModels.length > 0) {
        if ($scope.filterModels[0].column != null) {
          delete $scope.tableState.search.predicateObject;
          return true;
        }
      } else {
        return false;
      }
    };
    vm.clearFilters = function() {
      vm.createFilterFields();
      $scope.submitAdvancedFilters();
    };

    $scope.clearSearch = function() {
      delete $scope.tableState.search.predicateObject;
      $('#search-input')[0].value = '';
      $scope.getListViewData();
    };

    vm.expandIconClick = (row, event) => {
      if (row.package_type !== 1) {
        $scope.expandAic(row);
        event.stopPropagation();
      }
    };

    // AIC's
    $scope.expandedAics = [];
    $scope.expandAic = function(row) {
      row.collapsed = !row.collapsed;
      if (!row.collapsed) {
        $scope.expandedAics.push(row.object_identifier_value);
      } else {
        $scope.expandedAics.forEach(function(aic, index, array) {
          if (aic == row.object_identifier_value) {
            $scope.expandedAics.splice(index, 1);
          }
        });
      }
    };

    // Expand all IP's
    vm.expandAll = function() {
      vm.displayedIps.forEach(function(ip) {
        ip.collapsed = false;
        $scope.expandedAics.push(ip.object_identifier_value);
      });
    };

    vm.collapseAll = function() {
      vm.displayedIps.forEach(function(ip) {
        ip.collapsed = true;
        $scope.expandedAics.forEach(function(aic, index, array) {
          if (aic == ip.object_identifier_value) {
            $scope.expandedAics.splice(index, 1);
          }
        });
      });
    };

    vm.expandAllVisible = function() {
      let visible = false;
      let expand = true;
      vm.displayedIps.forEach(function(ip) {
        if (ip.information_packages && ip.information_packages.length) {
          visible = true;
          if (ip.collapsed == false) {
            expand = false;
          }
        }
      });
      vm.showExpand = expand;
      return visible;
    };
    // Remove ip
    $scope.ipRemoved = function(ipObject) {
      $scope.edit = false;
      $scope.select = false;
      $scope.eventlog = false;
      $scope.eventShow = false;
      $scope.statusShow = false;
      $scope.filebrowser = false;
      $scope.requestForm = false;
      if (vm.displayedIps.length == 0) {
        $state.reload();
      }
      $scope.getListViewData();
    };

    //Get data for eventlog view
    vm.getEventlogData = function() {
      listViewService.getEventlogData().then(function(value) {
        $scope.eventTypeCollection = value;
      });
    };

    $scope.updateIpsPerPage = function(items) {
      if (typeof items === 'number') {
        $cookies.put('essarch-ips-per-page', items);
      }
    };

    $scope.menuOptions = [];

    $scope.checkPermission = function(permissionName) {
      return !angular.isUndefined(PermPermissionStore.getPermissionDefinition(permissionName));
    };
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

    vm.multipleIpResponsible = function() {
      if ($scope.ips.length > 0) {
        var responsible = true;
        $scope.ips.forEach(function(ip) {
          if (ip.responsible.id !== $rootScope.auth.id) {
            responsible = false;
          }
        });
        return responsible;
      } else {
        return false;
      }
    };

    vm.allIncludedWithState = (list, state) => {
      return list.filter(x => x.state === state).length === list.length;
    };

    //Create and show modal for remove ip
    $scope.removeIpModal = function(ipObject) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/remove-ip-modal.html',
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
    vm.ipInformationModal = function(ip) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/ip_information_modal.html',
        controller: 'IpInformationModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return {
              ip: ip,
            };
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

    vm.changeOrganizationModal = function(ip) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/modals/change_organization_modal.html',
        controller: 'OrganizationModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'md',
        resolve: {
          data: function() {
            return {
              ip: ip,
            };
          },
        },
      });
      modalInstance.result
        .then(function(data) {
          $scope.getListViewData();
        })
        .catch(function() {
          $log.info('modal-component dismissed at: ' + new Date());
        });
    };

    vm.downloadOrderModal = function(order) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/download_order_modal.html',
        controller: 'OrderModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: function() {
            return {
              order: order,
              allow_close: true,
            };
          },
        },
      });
      modalInstance.result.catch(function() {
        $log.info('modal-component dismissed at: ' + new Date());
      });
    };

    vm.downloadDipModal = function(ip) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/download_dip_modal.html',
        controller: 'DownloadDipModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: function() {
            return {
              ip,
              allow_close: true,
            };
          },
        },
      });
      modalInstance.result.catch(function() {
        $log.info('modal-component dismissed at: ' + new Date());
      });
    };

    //advanced filter form data
    $scope.filterModel = {};
    $scope.options = {};

    //Toggle visibility of advanced filters
    $scope.toggleAdvancedFilters = function() {
      if ($scope.showAdvancedFilters) {
        $scope.showAdvancedFilters = false;
      } else {
        if ($scope.fields.length <= 0 || $scope.filterModel === null) {
          vm.createFilterFields();
        }
        $scope.showAdvancedFilters = true;
      }
      if ($scope.showAdvancedFilters) {
        $window.onclick = function(event) {
          const clickedElement = $(event.target);
          if (!clickedElement) return;
          const elementClasses = event.target.classList;
          const clickedOnAdvancedFilters =
            elementClasses.contains('filter-icon') ||
            elementClasses.contains('advanced-filters') ||
            elementClasses.contains('ui-select-match-text') ||
            elementClasses.contains('ui-select-search') ||
            elementClasses.contains('ui-select-toggle') ||
            elementClasses.contains('ui-select-choices') ||
            clickedElement.parents('.advanced-filters').length ||
            clickedElement.parents('.button-group').length;

          if (!clickedOnAdvancedFilters) {
            $scope.showAdvancedFilters = !$scope.showAdvancedFilters;
            $window.onclick = null;
            $scope.$apply();
          }
        };
      } else {
        $window.onclick = null;
      }
    };

    $scope.clearSearch = function() {
      delete $scope.tableState.search.predicateObject;
      $('#search-input')[0].value = '';
      $scope.getListViewData();
    };

    // Click function for request form submit.
    // Replaced form="vm.requestForm" to work in IE
    $scope.clickSubmit = function() {
      if (vm.requestForm.$valid) {
        $scope.submitRequest($scope.ip, vm.request);
      }
    };

    vm.canDeleteIP = function(row) {
      // IPs in workareas can always be deleted, including AICs
      if ($state.is('home.workarea')) {
        return true;
      }

      // Archived IPs requires a special permission to be deleted
      if (row.archived && !$scope.checkPermission('ip.delete_archived')) {
        return false;
      }

      // AICs cannot be deleted
      if (row.package_type_display == 'AIC' || row.package_type === undefined) {
        return false;
      }

      // Does the current user have permission to delete this IP?
      if (!row.permissions.includes('delete_informationpackage')) {
        return false;
      }

      // A special permission is required to delete first or last generation of an AIP
      if (row.package_type_display == 'AIP') {
        if (row.first_generation && !$scope.checkPermission('ip.delete_first_generation')) {
          return false;
        }

        if (row.last_generation && !$scope.checkPermission('ip.delete_last_generation')) {
          return false;
        }
      }

      return true;
    };
  }
}
