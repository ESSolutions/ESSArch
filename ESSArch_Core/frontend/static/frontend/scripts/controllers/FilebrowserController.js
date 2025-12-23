export default class FilebrowserController {
  constructor($scope, $rootScope, $sce, appConfig, listViewService, $uibModal, $window, $cookies, $state) {
    $scope.previousGridArrays = [];
    $scope.deckGridData = [];
    const vm = this;

    //Get File Browser settings
    function getFileBrowserView() {
      if ($rootScope.auth.file_browser_view_type) {
        if ($rootScope.auth.file_browser_view_type === 'grid') {
          $scope.listView = false;
          $scope.gridView = true;
        } else {
          $scope.listView = true;
          $scope.gridView = false;
        }
      } else {
        $scope.listView = true;
        $scope.gridView = false;
      }
    }

    vm.$onInit = function () {
      if (!$scope.ip) {
        $scope.ip = $rootScope.ip;
      }
      getFileBrowserView();
      $scope.gridArrayLoading = true;
    };

    vm.$onChanges = function (changes) {
      if (changes.user) {
        $scope.previousGridArrays = [];
        $scope.initLoad = true;
        $scope.initExpanded = false;
        $scope.dirPipe($scope.tableState);
      }
      if (changes.ip) {
        $scope.ip = $rootScope.ip;
      }
    };
    const watchers = [];
    vm.$onDestroy = function () {
      watchers.forEach(function (watcher) {
        watcher();
      });
    };
    $scope.listView = false;
    $scope.gridView = true;
    $scope.useListView = function () {
      $scope.listView = true;
      $scope.gridView = false;
    };

    $scope.useGridView = function () {
      $scope.listView = false;
      $scope.gridView = true;
    };

    $scope.filesPerPage = $cookies.get('files-per-page') || 50;
    $scope.changeFilesPerPage = function (filesPerPage) {
      if (typeof filesPerPage === 'number') {
        $cookies.put('files-per-page', filesPerPage, {expires: new Date('Fri, 31 Dec 9999 23:59:59 GMT')});
      }
    };

    $scope.previousGridArraysString = function () {
      if ($scope.ip) {
        let retString = '';
        $scope.previousGridArrays.forEach(function (card) {
          retString = retString.concat(card.name, '/');
        });
        return retString;
      }
    };

    $scope.dirPipe = function (tableState) {
      if (vm.browserstate) {
        vm.browserstate.path = $scope.previousGridArraysString();
        $rootScope.currentBrowserPath = vm.browserstate.path || '';
      }
      $scope.gridArrayLoading = true;
      if (!angular.isUndefined(tableState)) {
        $scope.tableState = tableState;
        const paginationParams = listViewService.getPaginationParams(tableState.pagination, $scope.filesPerPage);
        if ($state.includes('**.workarea.**')) {
          listViewService
            .getWorkareaDir(
              $scope.ip.id,
              vm.workarea,
              $scope.previousGridArraysString(),
              paginationParams,
              vm.user ? vm.user.id : null
            )
            .then(function (dir) {
              if (
                $scope.initLoad &&
                !$scope.initExpanded &&
                !$scope.ip.workarea[0].packaged &&
                $scope.ip.workarea[0].extracted
              ) {
                for (let i = 0; i < dir.data.length; i++) {
                  if (dir.data[i].name == $scope.ip.object_identifier_value) {
                    $scope.expandFile($scope.ip, dir.data[i]);
                    $scope.initExpanded = true;
                    break;
                  }
                }
              } else {
                $scope.deckGridData = dir.data;
                tableState.pagination.numberOfPages = dir.numberOfPages; //set the number of pages so the pagination can update
                $scope.gridArrayLoading = false;
                $scope.initLoad = false;
                $scope.openingNewPage = false;
              }
            });
        } else {
          listViewService.getDir($scope.ip, $scope.previousGridArraysString(), paginationParams).then(function (dir) {
            //console.log('$scope.ip: ' + JSON.stringify($scope.ip));
            if (
              $scope.initLoad &&
              !$scope.initExpanded &&
              $scope.ip.package_type_display == 'SIP' &&
              $scope.ip.state == 'Prepared'
            ) {
              for (let i = 0; i < dir.data.length; i++) {
                if (dir.data[i].name == 'content' || dir.data[i].name == 'c') {
                  $scope.expandFile($scope.ip, dir.data[i]);
                  $scope.initExpanded = true;
                  break;
                }
              }
              if (!$scope.initExpanded) {
                $scope.deckGridData = dir.data;
                tableState.pagination.numberOfPages = dir.numberOfPages; //set the number of pages so the pagination can update
                $scope.gridArrayLoading = false;
                $scope.initLoad = false;
                $scope.openingNewPage = false;
              }
            } else {
              $scope.deckGridData = dir.data;
              tableState.pagination.numberOfPages = dir.numberOfPages; //set the number of pages so the pagination can update
              $scope.gridArrayLoading = false;
              $scope.initLoad = false;
              $scope.openingNewPage = false;
            }
          });
        }
      }
    };

    $scope.$on('UPDATE_FILEBROWSER', function (data) {
      $scope.dirPipe($scope.tableState);
    });

    $scope.deckGridInit = function (ip) {
      $scope.previousGridArrays = [];
      if ($scope.tableState) {
        $scope.initLoad = true;
        $scope.initExpanded = false;
        $scope.dirPipe($scope.tableState);
        $scope.selectedCards = [];
      }
    };
    if ($rootScope.ip) {
      $scope.deckGridInit($rootScope.ip);
    }
    watchers.push(
      $scope.$watch(
        function () {
          return $rootScope.ip;
        },
        function (newValue, oldValue) {
          const old = angular.copy($scope.ip);
          $scope.ip = $rootScope.ip;
          if (old.id !== $rootScope.ip.id) {
            $scope.deckGridInit($rootScope.ip);
            $scope.previousGridArrays = [];
          }
        },
        true
      )
    );
    $scope.previousGridArray = function () {
      $scope.previousGridArrays.pop();
      if ($scope.tableState) {
        $scope.tableState.pagination.start = 0;
        $scope.openingNewPage = true;
        $scope.dirPipe($scope.tableState);
        $scope.selectedCards = [];
      }
    };
    $scope.updateGridArray = function (ip) {
      if ($scope.tableState) {
        $scope.dirPipe($scope.tableState);
      }
    };
    $scope.expandFile = function (ip, card, expandContainer) {
      if (
        card.type == 'dir' ||
        (card.name.endsWith('.tar') && expandContainer) ||
        (card.name.endsWith('.zip') && expandContainer)
      ) {
        $scope.previousGridArrays.push(card);
        if ($scope.tableState) {
          $scope.tableState.pagination.start = 0;
          $scope.openingNewPage = true;
          $scope.dirPipe($scope.tableState);
          $scope.selectedCards = [];
        }
      } else {
        $scope.getFile(card);
      }
    };
    $scope.selectedCards = [];

    function includesWithProperty(array, property, value) {
      for (let i = 0; i < array.length; i++) {
        if (array[i][property] === value) {
          return true;
        }
      }
      return false;
    }

    $scope.inWorkarea = function () {
      if ($state.includes('**.workarea.**')) {
        return true;
      } else {
        return false;
      }
    };

    $scope.selectedCardIsContainer = function () {
      let array = $scope.selectedCards;
      for (let i = 0; i < array.length; i++) {
        if (array[i]['name'].endsWith('.tar') || array[i]['name'].endsWith('.zip')) {
          return array[i];
        }
      }
      return false;
    };

    $scope.cardSelect = function (card) {
      if (includesWithProperty($scope.selectedCards, 'name', card.name)) {
        $scope.selectedCards.splice($scope.selectedCards.indexOf(card), 1);
      } else {
        $scope.selectedCards.push(card);
      }
    };

    function folderNameExistsModal(index, folder, fileToOverwrite) {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/folder-exists-modal.html',
        scope: $scope,
        controller: 'OverwriteModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: function () {
            return {
              file: folder,
              type: fileToOverwrite.type,
            };
          },
        },
      });
      modalInstance.result.then(function (data) {
        if ($state.includes('**.workarea.**')) {
          listViewService
            .deleteWorkareaFile(
              $scope.ip,
              vm.workarea,
              $scope.previousGridArraysString(),
              fileToOverwrite,
              vm.user ? vm.user.id : null
            )
            .then(function () {
              listViewService.addNewFolder($scope.ip, $scope.previousGridArraysString(), folder).then(function () {
                $scope.updateGridArray();
              });
            });
        } else {
          listViewService.deleteFile($scope.ip, $scope.previousGridArraysString(), fileToOverwrite).then(function () {
            listViewService.addNewFolder($scope.ip, $scope.previousGridArraysString(), folder).then(function () {
              $scope.updateGridArray();
            });
          });
        }
      });
    }

    $scope.createFolder = function (folderName) {
      const folder = {
        type: 'dir',
        name: folderName,
      };
      let fileExists = false;
      $scope.deckGridData.forEach(function (chosen, index) {
        if (chosen.name === folder.name) {
          fileExists = true;
          folderNameExistsModal(index, folder, chosen);
        }
      });
      if (!fileExists) {
        if ($state.includes('**.workarea.**')) {
          listViewService
            .addNewWorkareaFolder(
              $scope.ip,
              vm.workarea,
              $scope.previousGridArraysString(),
              folder,
              vm.user ? vm.user.id : null
            )
            .then(function (response) {
              $scope.updateGridArray();
            });
        } else {
          listViewService.addNewFolder($scope.ip, $scope.previousGridArraysString(), folder).then(function (response) {
            $scope.updateGridArray();
          });
        }
      }
    };

    $scope.getFile = function (file) {
      if ($state.includes('**.workarea.**')) {
        file.content = $sce.trustAsResourceUrl(
          appConfig.djangoUrl +
            'workarea-files/?id=' +
            $scope.ip.id +
            '&type=' +
            vm.workarea +
            '&path=' +
            encodeURIComponent($scope.previousGridArraysString() + file.name) +
            (vm.user ? '&user=' + vm.user.id : '')
        );
      } else if ($scope.ip.state == 'At reception') {
        file.content = $sce.trustAsResourceUrl(
          appConfig.djangoUrl +
            'ip-reception/' +
            $scope.ip.id +
            '/files/' +
            encodeURIComponent($scope.previousGridArraysString() + file.name)
        );
      } else {
        file.content = $sce.trustAsResourceUrl(
          appConfig.djangoUrl +
            'information-packages/' +
            $scope.ip.id +
            '/files/' +
            encodeURIComponent($scope.previousGridArraysString() + file.name)
        );
      }
      $window.open(file.content, '_blank');
    };

    $scope.newDirModal = function () {
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
      modalInstance.result.then(function (data) {
        $scope.createFolder(data.dir_name);
      });
    };
    $scope.removeFiles = function () {
      $scope.selectedCards.forEach(function (file) {
        if ($state.includes('**.workarea.**')) {
          listViewService
            .deleteWorkareaFile(
              $scope.ip,
              vm.workarea,
              $scope.previousGridArraysString(),
              file,
              vm.user ? vm.user.id : null
            )
            .then(function () {
              $scope.updateGridArray();
            });
        } else {
          listViewService.deleteFile($scope.ip, $scope.previousGridArraysString(), file).then(function () {
            $scope.updateGridArray();
          });
        }
      });
      $scope.selectedCards = [];
    };
    $scope.isSelected = function (card) {
      let cardClass = '';
      $scope.selectedCards.forEach(function (file) {
        if (card.name == file.name) {
          cardClass = 'card-selected';
        }
      });
      return cardClass;
    };
    $scope.getFileExtension = function (file) {
      return file.name.split('.').pop().toUpperCase();
    };
  }
}
