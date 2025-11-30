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

export default class CollectContentCtrl {
  constructor(
    IP,
    $log,
    $uibModal,
    $timeout,
    $scope,
    $rootScope,
    $window,
    appConfig,
    listViewService,
    $interval,
    $anchorScroll,
    $cookies,
    $controller,
    $transitions,
    $state,
    $translate
  ) {
    const vm = this;
    const ipSortString = ['Prepared', 'Uploading'];
    const params = {package_type: 0};

    $controller('BaseCtrl', {$scope: $scope, vm: vm, ipSortString, params});

    // -----------------------------------------------------------------------
    // BASIC PAGE STATE
    // -----------------------------------------------------------------------
    vm.uploading = false;
    vm.browserstate = {path: ''};
    $scope.showFileUpload = true;
    $scope.currentFlowObject = null;

    // -----------------------------------------------------------------------
    // GRID / FILEBROWSER REFRESH WATCHERS
    // -----------------------------------------------------------------------
    const watchers = [];
    let fileBrowserInterval;

    watchers.push(
      $scope.$watch(
        () => $scope.select,
        (newValue) => {
          if (newValue) {
            $interval.cancel(fileBrowserInterval);
            fileBrowserInterval = $interval(() => $scope.updateGridArray(), appConfig.fileBrowserInterval);
          } else {
            $interval.cancel(fileBrowserInterval);
          }
        }
      )
    );

    $transitions.onSuccess({}, () => {
      $interval.cancel(fileBrowserInterval);
      watchers.forEach((w) => w());
    });

    // -----------------------------------------------------------------------
    // CONTEXT MENU
    // -----------------------------------------------------------------------
    $scope.menuOptions = function () {
      return [
        {
          text: $translate.instant('INFORMATION_PACKAGE_INFORMATION'),
          click: () => vm.ipInformationModal($scope.ip),
        },
      ];
    };

    // Inside your controller
    $scope.rowHeight = 30; // px per row
    $scope.buffer = 50;
    $scope.visibleRows = [];
    $scope.folders = [];
    $scope.globalProgress = 0;

    // -----------------------------------------------------------------------
    // SELECT IP ROW
    // -----------------------------------------------------------------------
    vm.selectSingleRow = function (row, options) {
      $scope.ips = [];

      if ($scope.ip && $scope.ip.id === row.id) {
        // Unselect
        $scope.select = false;
        $scope.eventlog = false;
        $scope.ip = null;
        $rootScope.ip = null;
        if (!options || !options.noStateChange) {
          $state.go($state.current.name, {id: null});
        }
        $scope.filebrowser = false;
      } else {
        // New selection
        $scope.ip = row;
        $rootScope.ip = row;

        if (!options || !options.noStateChange) {
          $state.go($state.current.name, {id: row.id});
        }

        $scope.currentFlowObject = $rootScope.flowObjects[row.id];

        if ($scope.select) {
          $scope.showFileUpload = false;
          $timeout(() => ($scope.showFileUpload = true));
        }

        $scope.select = true;
        $scope.eventlog = true;
      }

      // Reset UI state
      $scope.previousGridArrays = [];
      $scope.uploadDisabled = false;
      $scope.eventShow = false;
      $scope.statusShow = false;
    };

    // -----------------------------------------------------------------------
    // VIEW UPDATE HELPERS
    // -----------------------------------------------------------------------
    $scope.updateListViewTimeout = (timeout) => {
      $timeout(() => $scope.getListViewData(), timeout);
    };

    $scope.updateGridArray = () => {
      $scope.$broadcast('UPDATE_FILEBROWSER', {});
    };

    // -----------------------------------------------------------------------
    // DIRECTORY CREATION
    // -----------------------------------------------------------------------
    $scope.createFolder = function (folderName) {
      const folder = {type: 'dir', name: folderName};
      let exists = false;

      $scope.deckGridData.forEach((entry, i) => {
        if (entry.name === folderName) {
          exists = true;
          showFolderExistsModal(i, folder, entry);
        }
      });

      if (!exists) {
        console.log('createFolder - vm.browserstate.path', vm.browserstate.path);
        listViewService.addNewFolder($scope.ip, vm.browserstate.path, folder).then(() => $scope.updateGridArray());
      }
    };

    function showFolderExistsModal(index, folder, existing) {
      const modal = $uibModal.open({
        templateUrl: 'static/frontend/views/folder-exists-modal.html',
        scope: $scope,
        controller: 'OverwriteModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: () => ({file: folder, type: existing.type}),
        },
      });

      modal.result.then(() => {
        console.log('showFolderExistsModal - vm.browserstate.path', vm.browserstate.path);
        listViewService
          .deleteFile($scope.ip, vm.browserstate.path, existing)
          .then(() =>
            listViewService.addNewFolder($scope.ip, vm.browserstate.path, folder).then(() => $scope.updateGridArray())
          );
      });
    }

    $scope.newDirModal = function () {
      const modal = $uibModal.open({
        templateUrl: 'static/frontend/views/new-dir-modal.html',
        scope: $scope,
        controller: 'ModalInstanceCtrl',
        controllerAs: '$ctrl',
      });

      modal.result.then((data) => $scope.createFolder(data.dir_name));
    };

    // -----------------------------------------------------------------------
    // MISC ACTIONS
    // -----------------------------------------------------------------------
    $scope.removeFiles = function () {
      $scope.selectedCards.forEach((file) => {
        console.log('remove - vm.browserstate.path', vm.browserstate.path);
        listViewService.deleteFile($scope.ip, vm.browserstate.path, file).then(() => $scope.updateGridArray());
      });
      $scope.selectedCards = [];
    };

    $scope.isSelected = (card) => ($scope.selectedCards.some((f) => f.name === card.name) ? 'card-selected' : '');

    $scope.resetUploadedFiles = () => ($scope.uploadedFiles = 0);

    $scope.getFileExtension = (file) => file.name.split('.').pop().toUpperCase();

    // -----------------------------------------------------------------------
    // OPEN EAD EDITOR
    // -----------------------------------------------------------------------
    $scope.openEadEditor = function (ip) {
      const w = 900;
      const h = 600;
      const left =
        $window.innerWidth / 2 - w / 2 + ($window.screenLeft !== undefined ? $window.screenLeft : screen.left);
      const top = $window.innerHeight / 2 - h / 2 + ($window.screenTop !== undefined ? $window.screenTop : screen.top);

      $window.open(
        `/static/edead/filledForm.html?id=${ip.id}`,
        'EAD',
        `scrollbars=yes,width=${w},height=${h},left=${left},top=${top}`
      );
    };

    $scope.currentBrowserPath = vm.browserstate.path || '';
    $scope.$watch(
      () => vm.browserstate.path,
      (newPath) => {
        console.log('Path changed:', newPath);
        $scope.currentBrowserPath = newPath || '';
        $rootScope.currentBrowserPath = newPath || '';
      }
    );
  }
}
