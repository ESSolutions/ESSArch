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

export default class ReceptionCtrl {
  constructor(
    IPReception,
    IP,
    ArchivePolicy,
    $log,
    $uibModal,
    $scope,
    appConfig,
    $state,
    $rootScope,
    listViewService,
    Resource,
    $translate,
    $controller,
    ContextMenuBase,
    SelectedIPUpdater,
    $transitions
  ) {
    var vm = this;
    var ipSortString = [];
    var watchers = [];
    $controller('BaseCtrl', {$scope: $scope, vm: vm, ipSortString: ipSortString});
    $controller('TagsCtrl', {$scope: $scope, vm: vm});
    $scope.includedIps = [];
    $scope.profileEditor = false;
    //Request form data
    $scope.initRequestData = function() {
      vm.request = {
        type: 'receive',
        purpose: '',
        archivePolicy: {
          value: null,
          options: [],
        },
        submissionAgreement: {
          value: null,
          options: [],
          disabled: false,
        },
        informationClass: null,
        allowUnknownFiles: false,
      };
    };
    $scope.initRequestData();
    $transitions.onSuccess({}, function($transition) {
      watchers.forEach(function(watcher) {
        watcher();
      });
    });

    $scope.menuOptions = function(rowType, row) {
      var methods = [];
      if (row.state === 'Prepared') {
        methods.push(
          ContextMenuBase.changeOrganization(function() {
            $scope.ip = row;
            $rootScope.ip = row;
            vm.changeOrganizationModal($scope.ip);
          })
        );
      }
      return methods;
    };

    $scope.updateTags = function() {
      $scope.tagsLoading = true;
      $scope.getArchives().then(function(result) {
        vm.tags.archive.options = result;
        $scope.requestForm = true;
        $scope.tagsLoading = false;
      });
    };

    $scope.archivePolicyChange = function() {
      vm.request.informationClass = vm.request.archivePolicy.value.information_class;
    };

    //Get data for status view

    /*******************************************/
    /*Piping and Pagination for List-view table*/
    /*******************************************/

    $scope.selectedProfileRow = {profile_type: '', class: ''};
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
        var pagination = tableState.pagination;
        var start = pagination.start || 0; // This is NOT the page number, but the index of item in the list that you want to use to display the table.
        var number = pagination.number || vm.itemsPerPage; // Number of entries showed per page.
        var pageNumber = start / number + 1;
        Resource.getReceptionPage(
          start,
          number,
          pageNumber,
          tableState,
          sorting,
          search,
          ipSortString,
          $scope.columnFilters
        )
          .then(function(result) {
            vm.displayedIps = result.data;
            tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
            $scope.ipLoading = false;
            $scope.initLoad = false;
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

              listViewService.checkPages('reception', number, filters).then(function(result) {
                tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
                tableState.pagination.start = result.numberOfPages * number - number;
                vm.callServer(tableState);
              });
            }
          });
      }
    };

    //Click function for Ip table
    vm.selectSingleRow = function(row) {
      if ($scope.ip !== null && $scope.ip.id == row.id) {
        $scope.ip = null;
        $rootScope.ip = null;
        $scope.profileEditor = false;
      } else {
        vm.deselectAll();
        if (row.url) {
          row.url = appConfig.djangoUrl + 'ip-reception/' + row.id + '/';
        }
        vm.sdModel = {};
        $scope.ip = row;
        $rootScope.ip = row;
        $scope.buildSdForm(row);
        $scope.getFileList(row);
      }
    };

    vm.sdModel = {};
    vm.sdFields = [
      {
        templateOptions: {
          type: 'text',
          label: 'Start date',
          disabled: true,
        },
        type: 'input',
        key: 'start_date',
      },
      {
        templateOptions: {
          type: 'text',
          label: 'End date',
          disabled: true,
        },
        type: 'input',
        key: 'end_date',
      },
      {
        templateOptions: {
          type: 'text',
          label: 'Archivist Organization',
          disabled: true,
        },
        type: 'input',
        key: 'archivist_organization',
      },
      {
        templateOptions: {
          type: 'text',
          label: 'Creator',
          disabled: true,
        },
        type: 'input',
        key: 'creator',
      },
      {
        templateOptions: {
          type: 'text',
          label: 'Submitter Organization',
          disabled: true,
        },
        type: 'input',
        key: 'submitter_organization',
      },
      {
        templateOptions: {
          type: 'text',
          label: 'Submitter Individual',
          disabled: true,
        },
        type: 'input',
        key: 'submitter_individual',
      },
      {
        templateOptions: {
          type: 'text',
          label: 'Producer Organization',
          disabled: true,
        },
        type: 'input',
        key: 'producer_organization',
      },
      {
        templateOptions: {
          type: 'text',
          label: 'Producer Individual',
          disabled: true,
        },
        type: 'input',
        key: 'producer_individual',
      },
      {
        templateOptions: {
          type: 'text',
          label: 'IP owner',
          disabled: true,
        },
        type: 'input',
        key: 'ip_owner',
      },
      {
        templateOptions: {
          type: 'text',
          label: 'Preservation Organization',
          disabled: true,
        },
        type: 'input',
        key: 'preservation_organization',
      },
      {
        templateOptions: {
          type: 'text',
          label: 'System Name',
          disabled: true,
        },
        type: 'input',
        key: 'system_name',
      },
      {
        templateOptions: {
          type: 'text',
          label: 'System Version',
          disabled: true,
        },
        type: 'input',
        key: 'system_version',
      },
      {
        templateOptions: {
          type: 'text',
          label: 'System Type',
          disabled: true,
        },
        type: 'input',
        key: 'system_type',
      },
    ];

    $scope.buildSdForm = function(ip) {
      vm.sdModel = {
        start_date: ip.start_date,
        end_date: ip.end_date,
        archivist_organization: ip.archivist_organization ? ip.archivist_organization.name : null,
        creator: ip.creator_organization,
        submitter_organization: ip.submitter_organization,
        submitter_individual: ip.submitter_individual,
        producer_organization: ip.producer_organization,
        producer_individual: ip.producer_individual,
        ip_owner: ip.ipowner_organization,
        preservation_organization: ip.preservation_organization,
        system_name: ip.system_name,
        system_version: ip.system_version,
        system_type: ip.system_type,
      };
    };
    $scope.getFileList = function(ip) {
      var array = [];
      var tempElement = {
        filename: ip.object_path,
        created: ip.create_date,
        size: ip.object_size,
      };
      array.push(tempElement);
      $scope.fileListCollection = array;
    };

    //Reload current view
    $scope.reloadPage = function() {
      $state.reload();
    };
    $scope.yes = $translate.instant('YES');
    $scope.no = $translate.instant('NO');

    $scope.getArchivePolicies = function() {
      return ArchivePolicy.query().$promise.then(function(data) {
        return data;
      });
    };

    // Remove ip
    $scope.removeIp = function(ipObject) {
      IP.delete({
        id: ipObject.id,
      }).$promise.then(function() {
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
        vm.uncheckIp(ipObject);
        $scope.getListViewData();
      });
    };

    //Create and show modal for remove ip
    $scope.receiveModal = function(ip) {
      vm.receiveModalLoading = true;
      if (angular.isUndefined(ip) && $scope.ip !== null) {
        ip = $scope.ip;
      }
      if (ip.state == 'At reception') {
        IPReception.get({id: ip.id}).$promise.then(function(resource) {
          if (resource.altrecordids.SUBMISSIONAGREEMENT) {
            IPReception.prepare({id: resource.id, submission_agreement: resource.altrecordids.SUBMISSIONAGREEMENT[0]})
              .$promise.then(function(prepared) {
                vm.receiveModalLoading = false;
                var modalInstance = $uibModal.open({
                  animation: true,
                  ariaLabelledBy: 'modal-title',
                  ariaDescribedBy: 'modal-body',
                  templateUrl: 'static/frontend/views/receive_modal.html',
                  controller: 'ReceiveModalInstanceCtrl',
                  size: 'lg',
                  scope: $scope,
                  controllerAs: '$ctrl',
                  resolve: {
                    data: function() {
                      return {
                        ip: prepared,
                        vm: vm,
                      };
                    },
                  },
                });
                modalInstance.result.then(
                  function(data) {
                    $scope.getListViewData();
                    if (data.status == 'received') {
                      $scope.eventlog = false;
                      $scope.edit = false;
                      $scope.requestForm = false;
                    }
                    $scope.filebrowser = false;
                    $scope.initRequestData();
                    $scope.getListViewData();
                    if ($scope.ips.length > 0) {
                      $scope.ips.shift();
                      $scope.getArchivePolicies().then(function(result) {
                        vm.request.archivePolicy.options = result;
                        $scope.getArchives().then(function(result) {
                          vm.tags.archive.options = result;
                          $scope.requestForm = true;
                          $scope.receiveModal($scope.ips[0]);
                        });
                      });
                    } else {
                      $scope.ip = null;
                      $rootScope.ip = null;
                    }
                  },
                  function() {
                    $scope.getListViewData();
                    $log.info('modal-component dismissed at: ' + new Date());
                  }
                );
              })
              .catch(function(response) {
                vm.receiveModalLoading = false;
              });
          } else {
            vm.receiveModalLoading = false;
            var modalInstance = $uibModal.open({
              animation: true,
              ariaLabelledBy: 'modal-title',
              ariaDescribedBy: 'modal-body',
              templateUrl: 'static/frontend/views/receive_modal.html',
              controller: 'ReceiveModalInstanceCtrl',
              size: 'lg',
              scope: $scope,
              controllerAs: '$ctrl',
              resolve: {
                data: function() {
                  return {
                    ip: resource,
                    vm: vm,
                  };
                },
              },
            });
            modalInstance.result.then(
              function(data) {
                $scope.getListViewData();
                if (data.status == 'received') {
                  $scope.eventlog = false;
                  $scope.edit = false;
                  $scope.requestForm = false;
                }
                $scope.filebrowser = false;
                $scope.initRequestData();
                $scope.getListViewData();
                if ($scope.ips.length > 0) {
                  $scope.ips.shift();
                  $scope.getArchivePolicies().then(function(result) {
                    vm.request.archivePolicy.options = result;
                    $scope.getArchives().then(function(result) {
                      vm.tags.archive.options = result;
                      $scope.requestForm = true;
                      $scope.receiveModal($scope.ips[0]);
                    });
                  });
                } else {
                  $scope.ip = null;
                  $rootScope.ip = null;
                }
              },
              function() {
                $scope.getListViewData();
                $log.info('modal-component dismissed at: ' + new Date());
              }
            );
          }
        });
      } else {
        IP.get({id: ip.id}).$promise.then(function(resource) {
          vm.receiveModalLoading = false;
          var modalInstance = $uibModal.open({
            animation: true,
            ariaLabelledBy: 'modal-title',
            ariaDescribedBy: 'modal-body',
            templateUrl: 'static/frontend/views/receive_modal.html',
            controller: 'ReceiveModalInstanceCtrl',
            size: 'lg',
            scope: $scope,
            controllerAs: '$ctrl',
            resolve: {
              data: function() {
                return {
                  ip: resource,
                  vm: vm,
                };
              },
            },
          });
          modalInstance.result.then(
            function(data) {
              $scope.getListViewData();
              if (data.status == 'received') {
                $scope.eventlog = false;
                $scope.edit = false;
                $scope.requestForm = false;
              }
              $scope.filebrowser = false;
              $scope.initRequestData();
              $scope.getListViewData();
              if ($scope.ips.length > 0) {
                $scope.ips.shift();
                $scope.getArchivePolicies().then(function(result) {
                  vm.request.archivePolicy.options = result;
                  $scope.getArchives().then(function(result) {
                    vm.tags.archive.options = result;
                    $scope.requestForm = true;
                    $scope.receiveModal($scope.ips[0]);
                  });
                });
              } else {
                $scope.ip = null;
                $rootScope.ip = null;
              }
            },
            function() {
              $scope.getListViewData();
              $log.info('modal-component dismissed at: ' + new Date());
            }
          );
        });
      }
    };

    $scope.informationClassAlert = null;
    $scope.alerts = {
      matchError: {type: 'danger', msg: $translate.instant('MATCH_ERROR')},
    };
    $scope.closeAlert = function() {
      $scope.informationClassAlert = null;
    };

    vm.uncheckAll = function() {
      $scope.includedIps = [];
      vm.displayedIps.forEach(function(row) {
        row.checked = false;
      });
    };

    $scope.clickSubmit = function() {
      if (vm.requestForm.$valid) {
        $scope.receive($scope.ips);
      }
    };
  }
}
