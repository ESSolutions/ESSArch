export default class {
  constructor(
    IP,
    StoragePolicy,
    $scope,
    $rootScope,
    $state,
    $controller,
    $cookies,
    $http,
    $interval,
    appConfig,
    $timeout,
    $anchorScroll,
    $uibModal,
    $translate,
    listViewService,
    Resource,
    $sce,
    $window,
    ContextMenuBase,
    SelectedIPUpdater,
    $transitions
  ) {
    const vm = this;
    const ipSortString = [];
    const watchers = [];
    $controller('BaseCtrl', {$scope: $scope, vm: vm, ipSortString: ipSortString, params: {}});
    vm.organizationMember = {
      current: null,
      options: [],
    };

    vm.listViewTitle = $translate.instant('DISSEMINATION_PACKAGES');

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
    $scope.orderObjects = [];
    listViewService.getOrderPage({pager: 'none'}).then(function(response) {
      $scope.orderObjects = response.data;
    });
    vm.itemsPerPage = $cookies.get('essarch-ips-per-page') || 10;
    $scope.initRequestData = function() {
      vm.request = {
        type: 'preserve',
        purpose: '',
        storagePolicy: {
          value: null,
          options: [],
        },
      };
    };
    $scope.initRequestData();

    $scope.getStoragePolicies = function() {
      return StoragePolicy.query().$promise.then(function(data) {
        return data;
      });
    };
    $scope.storagePolicyChange = function() {
      vm.request.informationClass = vm.request.storagePolicy.value.information_class;
    };
    //context menu data
    $scope.menuOptions = function(rowType, row) {
      return [
        ContextMenuBase.changeOrganization(function() {
          vm.changeOrganizationModal(row);
        }),
      ];
    };

    $scope.requestForm = false;
    $scope.openRequestForm = function(row) {
      $scope.getStoragePolicies().then(function(data) {
        vm.request.storagePolicy.options = data;
      });
    };

    //Cancel update intervals on state change
    $transitions.onSuccess({}, function($transition) {
      $interval.cancel(fileBrowserInterval);
      watchers.forEach(function(watcher) {
        watcher();
      });
    });

    //Initialize file browser update interval
    let fileBrowserInterval;
    watchers.push(
      $scope.$watch(
        function() {
          return $scope.select;
        },
        function(newValue, oldValue) {
          if (newValue) {
            $interval.cancel(fileBrowserInterval);
            fileBrowserInterval = $interval(function() {
              $scope.updateGridArray();
            }, appConfig.fileBrowserInterval);
          } else {
            $interval.cancel(fileBrowserInterval);
          }
        }
      )
    );
    /*******************************************/
    /*Piping and Pagination for List-view table*/
    /*******************************************/

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
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, vm.itemsPerPage);
        Resource.getDips(paginationParams, tableState, sorting, search, vm.columnFilters)
          .then(function(result) {
            vm.displayedIps = result.data;
            tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
            $scope.ipLoading = false;
            $scope.initLoad = false;
            SelectedIPUpdater.update(vm.displayedIps, $scope.ips, $scope.ip);
          })
          .catch(function(response) {
            if (response.status == 404) {
              const filters = angular.extend(
                {
                  state: ipSortString,
                  package_type: 4,
                },
                vm.columnFilters
              );

              listViewService.checkPages('ip', paginationParams.number, filters).then(function(result) {
                tableState.pagination.numberOfPages = result.numberOfPages; //set the number of pages so the pagination can update
                tableState.pagination.start = result.numberOfPages * paginationParams.number - paginationParams.number;
                vm.callServer(tableState);
              });
            }
          });
      }
    };

    // Click function for Ip table
    vm.selectSingleRow = function(row) {
      $scope.ips = [];
      if (row.state == 'Created') {
        $scope.openRequestForm(row);
      }
      if (row.state === 'Creating' || (($scope.select || $scope.requestForm) && $scope.ip && $scope.ip.id == row.id)) {
        $scope.select = false;
        $scope.eventlog = false;
        $scope.edit = false;
        $scope.ip = null;
        $rootScope.ip = null;
        $state.go($state.current.name, {id: null});
        $scope.filebrowser = false;
      } else {
        $scope.ip = row;
        $rootScope.ip = $scope.ip;
        $state.go($state.current.name, {id: $scope.ip.id});
        $scope.select = true;
        $scope.edit = true;
        $scope.filesPerPage = $cookies.get('files-per-page') || 50;
        $scope.dipFilesPerPage = $cookies.get('files-per-page') || 50;
        if ($scope.ip.state === 'Prepared') {
          $scope.deckGridInit(row);
        }
      }
      $scope.requestForm = false;
      $scope.requestEventlog = false;
      $scope.eventShow = false;
      $scope.statusShow = false;
    };
    $scope.colspan = 9;
    $scope.select = false;
    $scope.subSelect = false;
    $scope.edit = false;
    $scope.eventlog = false;
    $scope.requestForm = false;

    $scope.removeIp = function(ipObject) {
      IP.delete({
        id: ipObject.id,
      }).$promise.then(function() {
        vm.displayedIps.splice(vm.displayedIps.indexOf(ipObject), 1);
        $scope.edit = false;
        $scope.select = false;
        $scope.eventlog = false;
        $scope.eventShow = false;
        $scope.statusShow = false;
        if (vm.displayedIps.length == 0) {
          $state.reload();
        }
        $scope.getListViewData();
      });
    };

    //Deckgrid
    $scope.chosenFiles = [];
    $scope.chooseFiles = function(files) {
      let fileExists = false;
      files.forEach(function(file) {
        $scope.chosenFiles.forEach(function(chosen, index) {
          if (chosen.name === file.name) {
            fileExists = true;
            fileExistsModal(index, file, chosen);
          }
        });
        if (!fileExists) {
          listViewService
            .addFileToDip(
              $scope.ip,
              $scope.previousGridArraysString(1),
              file,
              $scope.previousGridArraysString(2),
              'access'
            )
            .then(function(result) {
              $scope.updateGridArray();
            });
        }
      });
      $scope.selectedCards1 = [];
    };

    vm.createDipModal = ip => {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/create_dip_modal.html',
        resolve: {
          data: function() {
            return {
              ip: ip,
            };
          },
        },
        controller: 'ModalInstanceCtrl',
        controllerAs: '$ctrl',
      });
      modalInstance.result.then(function(data) {
        $scope.select = false;
        $scope.edit = false;
        $scope.eventlog = false;
        $scope.selectedCards1 = [];
        $scope.selectedCards2 = [];
        $scope.chosenFiles = [];
        $scope.deckGridData = [];
        $timeout(function() {
          $scope.getListViewData();
          $scope.openRequestForm(ip);
          $anchorScroll();
        });
      });
    };

    function fileExistsModal(index, file, fileToBeOverwritten) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/file-exists-modal.html',
        scope: $scope,
        resolve: {
          data: function() {
            return {
              file: file,
              type: fileToBeOverwritten.type,
            };
          },
        },
        controller: 'OverwriteModalInstanceCtrl',
        controllerAs: '$ctrl',
      });
      modalInstance.result.then(function(data) {
        listViewService
          .addFileToDip(
            $scope.ip,
            $scope.previousGridArraysString(1),
            file,
            $scope.previousGridArraysString(2),
            'access'
          )
          .then(function(result) {
            $scope.updateGridArray();
          });
      });
    }

    function folderNameExistsModal(index, folder, fileToBeOverwritten) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/file-exists-modal.html',
        scope: $scope,
        controller: 'OverwriteModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: function() {
            return {
              file: folder,
              type: fileToBeOverwritten.type,
            };
          },
        },
      });
      modalInstance.result.then(function(data) {
        listViewService
          .deleteFile($scope.ip, $scope.previousGridArraysString(2), fileToBeOverwritten)
          .then(function() {
            listViewService.addNewFolder($scope.ip, $scope.previousGridArraysString(2), folder).then(function() {
              $scope.updateGridArray();
            });
          });
      });
    }

    $scope.removeFiles = function() {
      $scope.selectedCards2.forEach(function(file) {
        listViewService.deleteFile($scope.ip, $scope.previousGridArraysString(2), file).then(function() {
          $scope.updateGridArray();
        });
      });
      $scope.selectedCards2 = [];
    };

    $scope.createDipFolder = function(folderName) {
      const folder = {
        type: 'dir',
        name: folderName,
      };
      let fileExists = false;
      $scope.chosenFiles.forEach(function(chosen, index) {
        if (chosen.name === folder.name) {
          fileExists = true;
          folderNameExistsModal(index, folder, chosen);
        }
      });
      if (!fileExists) {
        listViewService.addNewFolder($scope.ip, $scope.previousGridArraysString(2), folder).then(function(response) {
          $scope.updateGridArray();
        });
      }
    };
    $scope.previousGridArrays1 = [];
    $scope.previousGridArrays2 = [];
    $scope.workareaListView = false;
    $scope.workareaGridView = true;
    $scope.dipListView = false;
    $scope.dipGridView = true;
    $scope.useListView = function(whichArray) {
      if (whichArray === 1) {
        $scope.workareaListView = true;
        $scope.workareaGridView = false;
        $scope.filesPerPage = $cookies.get('files-per-page') || 50;
      } else {
        $scope.dipListView = true;
        $scope.dipGridView = false;
        $scope.dipFilesPerPage = $cookies.get('files-per-page') || 50;
      }
    };

    $scope.useGridView = function(whichArray) {
      if (whichArray === 1) {
        $scope.workareaListView = false;
        $scope.workareaGridView = true;
        $scope.filesPerPage = $cookies.get('files-per-page') || 50;
      } else {
        $scope.dipListView = false;
        $scope.dipGridView = true;
        $scope.dipFilesPerPage = $cookies.get('files-per-page') || 50;
      }
    };

    $scope.changeFilesPerPage = function(filesPerPage) {
      $cookies.put('files-per-page', filesPerPage, {expires: new Date('Fri, 31 Dec 9999 23:59:59 GMT')});
    };
    $scope.previousGridArraysString = function(whichArray) {
      let retString = '';
      if (whichArray === 1) {
        $scope.previousGridArrays1.forEach(function(card) {
          retString = retString.concat(card.name, '/');
        });
      } else {
        $scope.previousGridArrays2.forEach(function(card) {
          retString = retString.concat(card.name, '/');
        });
      }
      return retString;
    };
    $scope.deckGridData = [];
    $scope.workareaPipe = function(tableState) {
      $scope.workArrayLoading = true;
      if ($scope.deckGridData.length == 0) {
        $scope.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        $scope.workarea_tableState = tableState;
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, 50);
        listViewService
          .getWorkareaDir(
            'access',
            $scope.previousGridArraysString(1),
            paginationParams.pageNumber,
            paginationParams.number,
            vm.organizationMember.current.id
          )
          .then(function(dir) {
            $scope.deckGridData = dir.data;
            $scope.workarea_tableState.pagination.numberOfPages = dir.numberOfPages; //set the number of pages so the pagination can update
            $scope.workArrayLoading = false;
            $scope.initLoad = false;
          })
          .catch(function(response) {
            if (response.status == 404) {
              $scope.deckGridData = [];
              $scope.workarea_tableState.pagination.numberOfPages = 0; //set the number of pages so the pagination can update
              $scope.workarea_tableState.pagination.start = 0; //set the number of pages so the pagination can update
              $scope.workArrayLoading = false;
              $scope.initLoad = false;
            }
          });
      }
    };
    $scope.dipPipe = function(tableState) {
      $scope.gridArrayLoading = true;
      if ($scope.deckGridData.length == 0) {
        $scope.initLoad = true;
      }
      if (!angular.isUndefined(tableState)) {
        $scope.dip_tableState = tableState;
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, 50);
        listViewService
          .getDipDir(
            $scope.ip,
            $scope.previousGridArraysString(2),
            paginationParams.pageNumber,
            paginationParams.number
          )
          .then(function(dir) {
            $scope.chosenFiles = dir.data;
            $scope.dip_tableState.pagination.numberOfPages = dir.numberOfPages; //set the number of pages so the pagination can update
            $scope.gridArrayLoading = false;
            $scope.initLoad = false;
          });
      }
    };
    $scope.deckGridInit = function(ip) {
      $scope.previousGridArrays1 = [];
      $scope.previousGridArrays2 = [];
      if ($scope.dip_tablestate && $sope.workarea_tablestate) {
        $scope.workareaPipe($scope.workarea_tableState);
        $scope.dipPipe($scope.dip_tableState);
      }
    };

    $scope.resetWorkareaGridArrays = function() {
      $scope.previousGridArrays1 = [];
    };

    $scope.previousGridArray = function(whichArray) {
      if (whichArray == 1) {
        $scope.previousGridArrays1.pop();
        $scope.workarea_tableState.pagination.start = 0;
        $scope.workareaPipe($scope.workarea_tableState);
      } else {
        $scope.previousGridArrays2.pop();
        $scope.dip_tableState.pagination.start = 0;
        $scope.dipPipe($scope.dip_tableState);
      }
    };
    $scope.workArrayLoading = false;
    $scope.dipArrayLoading = false;
    $scope.updateGridArray = function() {
      $scope.updateWorkareaFiles();
      $scope.updateDipFiles();
    };
    $scope.updateWorkareaFiles = function() {
      if ($scope.workarea_tableState) {
        $scope.workareaPipe($scope.workarea_tableState);
      }
    };
    $scope.updateDipFiles = function() {
      if ($scope.dip_tableState) {
        $scope.dipPipe($scope.dip_tableState);
      }
    };
    $scope.expandFile = function(whichArray, ip, card) {
      if (card.type == 'dir') {
        if (whichArray == 1) {
          $scope.selectedCards1 = [];
          $scope.previousGridArrays1.push(card);
          if ($scope.workarea_tableState) {
            $scope.workarea_tableState.pagination.start = 0;
            $scope.workareaPipe($scope.workarea_tableState);
            $scope.selectedCards = [];
          }
        } else {
          $scope.selectedCards2 = [];
          $scope.previousGridArrays2.push(card);
          if ($scope.dip_tableState) {
            $scope.dip_tableState.pagination.start = 0;
            $scope.dipPipe($scope.dip_tableState);
            $scope.selectedCards = [];
          }
        }
      } else {
        $scope.getFile(whichArray, card);
      }
    };
    $scope.getFile = function(whichArray, file) {
      if (whichArray == 1) {
        file.content = $sce.trustAsResourceUrl(
          appConfig.djangoUrl +
            'workarea-files/?type=access&path=' +
            $scope.previousGridArraysString(1) +
            file.name +
            (vm.organizationMember.current ? '&user=' + vm.organizationMember.current.id : '')
        );
      } else {
        file.content = $sce.trustAsResourceUrl(
          appConfig.djangoUrl +
            'information-packages/' +
            $scope.ip.id +
            '/files/?path=' +
            $scope.previousGridArraysString(2) +
            file.name
        );
      }
      $window.open(file.content, '_blank');
    };
    $scope.selectedCards1 = [];
    $scope.selectedCards2 = [];
    $scope.cardSelect = function(whichArray, card) {
      if (whichArray == 1) {
        if (includesWithProperty($scope.selectedCards1, 'name', card.name)) {
          $scope.selectedCards1.splice($scope.selectedCards1.indexOf(card), 1);
        } else {
          $scope.selectedCards1.push(card);
        }
      } else {
        if (includesWithProperty($scope.selectedCards2, 'name', card.name)) {
          $scope.selectedCards2.splice($scope.selectedCards2.indexOf(card), 1);
        } else {
          $scope.selectedCards2.push(card);
        }
      }
    };

    function includesWithProperty(array, property, value) {
      for (let i = 0; i < array.length; i++) {
        if (array[i][property] === value) {
          return true;
        }
      }
      return false;
    }

    $scope.isSelected = function(whichArray, card) {
      let cardClass = '';
      if (whichArray == 1) {
        $scope.selectedCards1.forEach(function(file) {
          if (card.name == file.name) {
            cardClass = 'card-selected';
          }
        });
      } else {
        $scope.selectedCards2.forEach(function(file) {
          if (card.name == file.name) {
            cardClass = 'card-selected';
          }
        });
      }
      return cardClass;
    };

    $scope.getFileExtension = function(file) {
      return file.name
        .split('.')
        .pop()
        .toUpperCase();
    };
    $scope.prepareDipModal = function() {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/prepare-dip-modal.html',
        scope: $scope,
        controller: 'ModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {},
        },
      });
      modalInstance.result.then(function(data) {
        $timeout(function() {
          $scope.getListViewData();
        });
      });
    };

    $scope.newDirModal = function() {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/new-dir-modal.html',
        scope: $scope,
        controller: 'ModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {},
        },
      });
      modalInstance.result.then(function(data) {
        $scope.createDipFolder(data.dir_name);
      });
    };
  }
}
