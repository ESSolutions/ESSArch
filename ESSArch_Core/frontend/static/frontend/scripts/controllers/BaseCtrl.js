/*
    ESSArch is an open source archiving and digital preservation system

    ESSArch Preservation Platform (EPP)
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

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
    $transitions
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
    vm.itemsPerPage = $cookies.get('epp-ips-per-page') || 10;
    vm.archived = false;
    vm.specificTabs = [];

    $scope.$translate = $translate;

    $scope.ContentTabs = ContentTabs;
    // Can be overwritten in controllers to change title
    vm.listViewTitle = $translate.instant('INFORMATION_PACKAGES');

    var watchers = [];
    // Init request form

    var docStateMap = {
      reception: 'reception.html',
      approval: 'approval.html',
      accessIp: 'access-search.html',
      workarea: 'access-workspace.html',
      createDip: 'dissemination.html',
      orders: 'index.html',
    };
    vm.getStateDocPage = function() {
      var page = $state.current.name.split('.').pop();
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

    // Watchers
    watchers.push(
      $scope.$watch(
        function() {
          return $rootScope.selectedTag;
        },
        function(newVal, oldVal) {
          $scope.getListViewData();
        },
        true
      )
    );

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
    $transitions.onSuccess({}, function($transition) {
      $interval.cancel(listViewInterval);
      watchers.forEach(function(watcher) {
        watcher();
      });
    });

    $scope.$on('REFRESH_LIST_VIEW', function(event, data) {
      $scope.getListViewData();
    });

    // list view update interval

    //Update ip list view with an interval
    //Update only if status < 100 and no step has failed in any IP
    var listViewInterval;
    vm.updateListViewConditional = function() {
      $interval.cancel(listViewInterval);
      listViewInterval = $interval(function() {
        var updateVar = false;
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
            var updateVar = false;
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
        }
        var sorting = tableState.sort;
        if (ipSortString.indexOf('Deleting') === -1) {
          ipSortString.push('Deleting'); // Add deleting if not already exists
        }
        let paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.itemsPerPage);
        Resource.getIpPage(
          paginationParams.start,
          paginationParams.number,
          paginationParams.pageNumber,
          params,
          sorting,
          search,
          ipSortString,
          $scope.expandedAics,
          $scope.columnFilters,
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
              var filters = angular.extend(
                {
                  state: ipSortString,
                },
                $scope.columnFilters
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

    function ipExists() {
      if ($scope.ip != null) {
        var temp = false;
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
      var index = 0;
      var inChildren = false;
      var parent = null;
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
      var index = vm.displayedIps.length - 1;
      var parent = null;
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
    var arrowLeft = 37;
    var arrowUp = 38;
    var arrowRight = 39;
    var arrowDown = 40;
    var escape = 27;
    var enter = 13;
    var space = 32;

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
            options: [{name: translations.YES, value: true}, {name: translations.NO, value: false}],
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
        case 'diff_check':
          console.log('request not implemented');
          break;
        default:
          console.log('request not matched');
          break;
      }
    };

    vm.preserveModal = function(ip, request) {
      var ips = null;
      if (Array.isArray(ip)) {
        ips = ip;
      }
      var modalInstance = $uibModal.open({
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
      var ips = null;
      if (Array.isArray(ip)) {
        ips = ip;
      }
      var modalInstance = $uibModal.open({
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
      var ips = null;
      if (Array.isArray(ip)) {
        ips = ip;
      }
      var modalInstance = $uibModal.open({
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
      var params = {purpose: request.purpose};
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
      var data = {
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
      var data = {purpose: request.purpose};
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
    $scope.ipTableClick = function(row, event) {
      if (event && event.shiftKey) {
        vm.shiftClickrow(row);
      } else if (event && event.ctrlKey) {
        vm.ctrlClickRow(row);
      } else {
        vm.selectSingleRow(row);
      }
    };

    vm.shiftClickrow = function(row) {
      var index = vm.displayedIps
        .map(function(ip) {
          return ip.id;
        })
        .indexOf(row.id);
      var last;
      if ($scope.ips.length > 0) {
        last = $scope.ips[$scope.ips.length - 1].id;
      } else if ($scope.ips.length <= 0 && $scope.ip != null) {
        last = $scope.ip.id;
      } else {
        last = null;
      }
      var lastIndex =
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
        var deleted = false;
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

    vm.selectSingleRow = function(row) {
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
        } else {
          $scope.ip = row;
          $rootScope.ip = $scope.ip;
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
      } else {
        $scope.select = true;
        $scope.eventlog = true;
        $scope.edit = true;
        $scope.requestForm = true;
        $scope.eventShow = false;
        $scope.ip = row;
        $rootScope.ip = $scope.ip;
      }
      $scope.statusShow = false;
    };

    $scope.selectedAmongOthers = function(id) {
      var exists = false;
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
      vm.setupForm();
      $scope.submitAdvancedFilters();
    };

    $scope.clearSearch = function() {
      delete $scope.tableState.search.predicateObject;
      $('#search-input')[0].value = '';
      $scope.getListViewData();
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
      var visible = false;
      var expand = true;
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
      $cookies.put('epp-ips-per-page', items);
    };

    $scope.menuOptions = [];

    $scope.checkPermission = function(permissionName) {
      return !angular.isUndefined(PermPermissionStore.getPermissionDefinition(permissionName));
    };
    $scope.extendedEqual = function(specification_data, model) {
      var returnValue = true;
      for (var prop in model) {
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

    //Modal functions
    $scope.tracebackModal = function(profiles) {
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
          data: {},
        },
      });
      modalInstance.result.then(
        function(data) {},
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    //Creates and shows modal with task information
    $scope.taskInfoModal = function() {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/modals/task_info_modal.html',
        scope: $scope,
        controller: 'TaskInfoModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {},
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {},
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    //Creates and shows modal with step information
    $scope.stepInfoModal = function() {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/modals/step_info_modal.html',
        scope: $scope,
        controller: 'StepInfoModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {},
        },
      });
      modalInstance.result.then(
        function(data, $ctrl) {},
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    //Create and show modal for remove ip
    $scope.removeIpModal = function(ipObject) {
      var modalInstance = $uibModal.open({
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
      var modalInstance = $uibModal.open({
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
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/modals/change_organization_modal.html',
        controller: 'OrganizationModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'sm',
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

    //advanced filter form data
    $scope.columnFilters = {};
    $scope.filterModel = {};
    $scope.options = {};
    $scope.fields = [];
    vm.setupForm = function() {
      $scope.fields = [];
      $scope.filterModel = {};
      for (var key in $scope.usedColumns) {
        var column = $scope.usedColumns[key];
        if (key == 'package_type_name_exclude') {
          delete $scope.usedColumns[key];
        } else {
          switch (column.type) {
            case 'ModelMultipleChoiceFilter':
            case 'MultipleChoiceFilter':
              $scope.fields.push({
                templateOptions: {
                  type: 'text',
                  label: column.label,
                  labelProp: 'display_name',
                  valueProp: 'value',
                  options: column.choices,
                },
                type: 'select',
                key: key,
              });
              break;
            case 'BooleanFilter':
              $scope.fields.push({
                templateOptions: {
                  label: column.label,
                  labelProp: key,
                  valueProp: key,
                },
                type: 'checkbox',
                key: key,
              });
              break;
            case 'ListFilter':
            case 'CharFilter':
              $scope.fields.push({
                templateOptions: {
                  type: 'text',
                  label: column.label,
                  labelProp: key,
                  valueProp: key,
                },
                type: 'input',
                key: key,
              });
              break;
            case 'IsoDateTimeFromToRangeFilter':
              $scope.fields.push({
                templateOptions: {
                  type: 'text',
                  label: column.label + ' ' + $translate.instant('START'),
                },
                type: 'datepicker',
                key: key + '_after',
              });
              $scope.fields.push({
                templateOptions: {
                  type: 'text',
                  label: column.label + ' ' + $translate.instant('END'),
                },
                type: 'datepicker',
                key: key + '_before',
              });
              break;
          }
        }
      }
    };

    vm.toggleOwnIps = function(filterIps) {
      if (filterIps) {
        $scope.filterModel.responsible = $rootScope.auth.username;
      } else {
        if ($scope.filterModel.responsible == $rootScope.auth.username) {
          delete $scope.filterModel.responsible;
        }
      }
    };

    //Toggle visibility of advanced filters
    $scope.toggleAdvancedFilters = function() {
      if ($scope.showAdvancedFilters) {
        $scope.showAdvancedFilters = false;
      } else {
        if ($scope.fields.length <= 0) {
          $http({
            method: 'OPTIONS',
            url: appConfig.djangoUrl + 'information-packages/',
          }).then(function(response) {
            $scope.usedColumns = response.data.filters;
            vm.setupForm();
          });
        }
        $scope.showAdvancedFilters = true;
      }
      if ($scope.showAdvancedFilters) {
        $window.onclick = function(event) {
          var clickedElement = $(event.target);
          if (!clickedElement) return;
          var elementClasses = event.target.classList;
          var clickedOnAdvancedFilters =
            elementClasses.contains('filter-icon') ||
            elementClasses.contains('advanced-filters') ||
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

    $scope.filterActive = function() {
      var temp = false;
      for (var key in $scope.columnFilters) {
        if ($scope.columnFilters[key] !== '' && $scope.columnFilters[key] !== null) {
          temp = true;
        }
      }
      return temp;
    };

    $scope.submitAdvancedFilters = function() {
      $scope.columnFilters = angular.copy($scope.filterModel);
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
      if ($state.is('home.ingest.workarea') || $state.is('home.access.workarea')) {
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
