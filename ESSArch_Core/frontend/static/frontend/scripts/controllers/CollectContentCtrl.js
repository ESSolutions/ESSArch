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

import * as Flow from '@flowjs/ng-flow/dist/ng-flow-standalone';

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
    const params = {
      package_type: 0,
    };
    $controller('BaseCtrl', {$scope: $scope, vm: vm, ipSortString: ipSortString, params});

    $scope.menuOptions = function (rowType, row) {
      const methods = [];
      methods.push({
        text: $translate.instant('INFORMATION_PACKAGE_INFORMATION'),
        click: function ($itemScope, $event, modelValue, text, $li) {
          vm.ipInformationModal(row);
        },
      });
      return methods;
    };

    vm.uploading = false;
    vm.flowDestination = null;
    $scope.showFileUpload = true;
    $scope.currentFlowObject = null;
    vm.browserstate = {
      path: '',
    };
    const watchers = [];
    // File browser interval
    let fileBrowserInterval;
    watchers.push(
      $scope.$watch(
        function () {
          return $scope.select;
        },
        function (newValue, oldValue) {
          if (newValue) {
            $interval.cancel(fileBrowserInterval);
            fileBrowserInterval = $interval(function () {
              $scope.updateGridArray();
            }, appConfig.fileBrowserInterval);
          } else {
            $interval.cancel(fileBrowserInterval);
          }
        }
      )
    );
    $transitions.onSuccess({}, function ($transition) {
      $interval.cancel(fileBrowserInterval);
      watchers.forEach(function (watcher) {
        watcher();
      });
    });

    vm.uploadCompletedModal = function (ip) {
      const ips = $scope.ips.length > 0 ? $scope.ips : null;
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/upload_completed_modal.html',
        scope: $scope,
        controller: 'DataModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            ip: ip,
            ips: ips,
          },
        },
      });
      modalInstance.result.then(
        function (data) {
          $scope.ips = [];
          $scope.ip = null;
          $rootScope.ip = null;
          $scope.getListViewData();
          vm.updateListViewConditional();
          $anchorScroll();
        },
        function () {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };

    //Click function for ip table
    vm.selectSingleRow = function (row, options) {
      $scope.ips = [];
      if ($scope.ip !== null && $scope.ip.id == row.id) {
        $scope.select = false;
        $scope.eventlog = false;
        $scope.ip = null;
        $rootScope.ip = null;
        if (angular.isUndefined(options) || !options.noStateChange) {
          $state.go($state.current.name, {id: null});
        }
        $scope.filebrowser = false;
      } else {
        $scope.ip = row;
        $rootScope.ip = row;
        if (angular.isUndefined(options) || !options.noStateChange) {
          $state.go($state.current.name, {id: $scope.ip.id});
        }
        if (!$rootScope.flowObjects[row.id]) {
          $scope.createNewFlow(row);
        }
        $scope.currentFlowObject = $rootScope.flowObjects[row.id];
        if ($scope.select) {
          $scope.showFileUpload = false;
          $timeout(function () {
            $scope.showFileUpload = true;
          });
        }
        $scope.select = true;
        $scope.eventlog = true;
      }
      $scope.previousGridArrays = [];
      $scope.uploadDisabled = false;
      $scope.eventShow = false;
      $scope.statusShow = false;
    };

    //UPLOAD
    $scope.updateListViewTimeout = function (timeout) {
      $timeout(function () {
        $scope.getListViewData();
      }, timeout);
    };
    //Deckgrid test

    $scope.updateGridArray = function (ip) {
      $scope.$broadcast('UPDATE_FILEBROWSER', {});
    };

    function includesWithProperty(array, property, value) {
      for (i = 0; i < array.length; i++) {
        if (array[i][property] === value) {
          return true;
        }
      }
      return false;
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
        listViewService.addNewFolder($scope.ip, vm.browserstate.path, folder).then(function (response) {
          $scope.updateGridArray();
        });
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
        listViewService.deleteFile($scope.ip, vm.browserstate.path, fileToOverwrite).then(function () {
          listViewService.addNewFolder($scope.ip, vm.browserstate.path, folder).then(function () {
            $scope.updateGridArray();
          });
        });
      });
    }
    $scope.newDirModal = function () {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/new-dir-modal.html',
        scope: $scope,
        controller: 'ModalInstanceCtrl',
        controllerAs: '$ctrl',
      });
      modalInstance.result.then(function (data) {
        $scope.createFolder(data.dir_name);
      });
    };

    $scope.openEadEditor = function (ip) {
      // Fixes dual-screen position                         Most browsers      Firefox
      const w = 900;
      const h = 600;
      const dualScreenLeft = $window.screenLeft != undefined ? $window.screenLeft : screen.left;
      const dualScreenTop = $window.screenTop != undefined ? $window.screenTop : screen.top;

      const width = $window.innerWidth
        ? $window.innerWidth
        : document.documentElement.clientWidth
        ? document.documentElement.clientWidth
        : screen.width;
      const height = $window.innerHeight
        ? $window.innerHeight
        : document.documentElement.clientHeight
        ? document.documentElement.clientHeight
        : screen.height;

      const left = width / 2 - w / 2 + dualScreenLeft;
      const top = height / 2 - h / 2 + dualScreenTop;
      $window.open(
        '/static/edead/filledForm.html?id=' + ip.id,
        'Levente',
        'scrollbars=yes, width=' + w + ', height=' + h + ', top=' + top + ', left=' + left
      );
    };
    $scope.getFlowTarget = function () {
      return appConfig.djangoUrl + 'information-packages/' + $scope.ip.id + '/upload/';
    };
    $scope.getQuery = function (FlowFile, FlowChunk, isTest) {
      return {destination: vm.browserstate.path};
    };
    $scope.fileUploadSuccess = function (ip, file, message, flow) {
      $scope.uploadedFiles++;
      const path = flow.opts.query.destination + file.relativePath;

      IP.mergeChunks({
        id: ip.id,
        path: path,
      });
    };
    $scope.fileTransferFilter = function (file) {
      return file.isUploading();
    };
    $scope.removeFiles = function () {
      $scope.selectedCards.forEach(function (file) {
        listViewService.deleteFile($scope.ip, vm.browserstate.path, file).then(function () {
          $scope.updateGridArray();
        });
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
    $scope.resetUploadedFiles = function () {
      $scope.uploadedFiles = 0;
    };
    $scope.uploadedFiles = 0;
    $scope.flowCompleted = false;
    $scope.flowComplete = function (flow, transfers) {
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
    $scope.hideFlowCompleted = function (flow) {
      flow.flowCompleted = false;
    };
    $scope.getUploadedPercentage = function (totalSize, uploadedSize, totalFiles) {
      if (totalSize == 0 || uploadedSize / totalSize == 1) {
        return ($scope.uploadedFiles / totalFiles) * 100;
      } else {
        return (uploadedSize / totalSize) * 100;
      }
    };

    $scope.getFileExtension = function (file) {
      return file.name.split('.').pop().toUpperCase();
    };
    $scope.createNewFlow = function (ip) {
      const flowObj = new Flow({
        target: appConfig.djangoUrl + 'information-packages/' + ip.id + '/upload/',
        simultaneousUploads: 15,
        chunkSize: 10 * 1024 * 1024, // 50MB
        maxChunkRetries: 5,
        chunkRetryInterval: 1000,
        headers: {'X-CSRFToken': $cookies.get('csrftoken')},
        complete: $scope.flowComplete,
      });
      flowObj.on('complete', function () {
        vm.uploading = false;
        $scope.flowComplete(flowObj, flowObj.files);
      });
      flowObj.on('fileSuccess', function (file, message) {
        $scope.fileUploadSuccess(ip, file, message, flowObj);
      });
      flowObj.on('uploadStart', function () {
        vm.uploading = true;
        flowObj.opts.query = {destination: vm.browserstate.path};
      });
      $rootScope.flowObjects[ip.id] = flowObj;
    };
  }
}
