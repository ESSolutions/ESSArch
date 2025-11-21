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

    $scope.onUploadError = function (file, message, flow) {
      let cleanMessage = 'Upload failed';

      // Try JSON
      try {
        const json = JSON.parse(message);
        if (json.error) cleanMessage = json.error;
        else if (json.detail) cleanMessage = json.detail;
      } catch (e) {
        // Strip HTML and truncate
        cleanMessage = message.replace(/<\/?[^>]+(>|$)/g, '');
        cleanMessage = cleanMessage.substring(0, 80) + '...';
      }

      file.errorMessage = cleanMessage;
      file.progress = () => 0;
      file.error = true;
      $scope.$applyAsync();
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
    $scope.resetUploadedFiles = function (ip) {
      $scope.uploadedFiles = 0;
    };
    $scope.uploadedFiles = 0;
    $scope.flowCompleted = false;
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

    $scope.cancelFile = function (file, flowObj) {
      // 1. Cancel Flow.js internal upload
      file.cancel();

      // 2. Remove from Flow.js file array
      const idx = flowObj.files.indexOf(file);
      if (idx !== -1) {
        flowObj.files.splice(idx, 1);
      }

      // 3. Adjust internal counters
      flowObj.filesToUpload--;

      // If file was already finished uploading before cancel
      if (file.isComplete && flowObj.filesFinished > 0) {
        flowObj.filesFinished--;
      }

      // 4. Prevent merge logic from running prematurely
      if (flowObj.filesFinished === flowObj.filesToUpload) {
        console.log('Updated counts after cancel: waiting for remaining uploads.');
      }

      // 5. Refresh Angular view
      $scope.$applyAsync();
    };

    $scope.retryFile = function (file) {
      file.retryingUpload = true;
      file.errorMessage = null;
      file.isError = false;
      file.mergeCompleted = false;

      file.retry();
    };

    $scope.createNewFlow = function (ip) {
      const flowObj = new Flow({
        target: appConfig.djangoUrl + 'information-packages/' + ip.id + '/upload/',
        simultaneousUploads: 15,
        chunkSize: 10 * 1024 * 1024,
        maxChunkRetries: 5,
        chunkRetryInterval: 1000,
        headers: {'X-CSRFToken': $cookies.get('csrftoken')},
      });

      //---------------------------------------------------------
      // DEBUGGING (REMOVE IF YOU WANT)
      //---------------------------------------------------------
      flowObj.on('fileAdded', (f) => console.log('fileAdded:', f.name));
      flowObj.on('filesSubmitted', (f) => console.log('filesSubmitted:', f.length));
      flowObj.on('uploadStart', () => console.log('uploadStart'));
      flowObj.on('fileProgress', (f) => console.log('fileProgress:', f.name, f.progress()));
      flowObj.on('fileSuccess', (f) => console.log('fileSuccess:', f.name));
      flowObj.on('fileError', (f, msg) => console.log('fileError:', f.name, msg));

      //---------------------------------------------------------
      // 1) FILES SELECTED — show them in table immediately
      //---------------------------------------------------------
      $scope.uploadedFiles = 0;
      // flowObj.filesFinished = 0;
      flowObj.filesToUpload = 0;

      flowObj.on('filesSubmitted', function (files) {
        flowObj.filesToUpload = files.length;

        files.forEach((file) => {
          file.mergeCompleted = false;
          file.isError = false;
          file.errorMessage = null;
        });

        $scope.$applyAsync();
      });

      //---------------------------------------------------------
      // 2) UPLOAD STARTED
      //---------------------------------------------------------
      flowObj.on('uploadStart', function () {
        vm.uploading = true;
        flowObj.opts.query = {destination: vm.browserstate.path};
      });

      //---------------------------------------------------------
      // 3) A FILE FINISHED UPLOADING ITS CHUNKS
      //    DO NOT MERGE YET — only count completion
      //---------------------------------------------------------
      flowObj.on('fileSuccess', function (file, message) {
        // This is a RETRY upload (only one file uploaded)
        if (file.retryingUpload) {
          file.wasRetried = true;
          const path = flowObj.opts.query.destination + file.relativePath;
          mergeFile(ip, path)
            .then(() => {
              file.mergeCompleted = true;
              file.isError = false;
              file.errorMessage = null;
              finalizeUpload(ip, flowObj, [file]);
            })
            .catch((error) => {
              file.isError = true;
              file.errorMessage = `Merge failed: ${error.status} ${error.statusText}`;
              file.progress = () => 0;
              file.mergeCompleted = false;
            })
            .finally(() => {
              file.retryingUpload = false;
              $scope.$applyAsync();
            });

          return; // prevent it from flowing into main batch logic
        }

        // ----- ORIGINAL batch upload logic -----
        $scope.uploadedFiles++;

        console.log('File uploaded: ' + file.name + ' (' + $scope.uploadedFiles + '/' + flowObj.filesToUpload + ')');
        // When ALL files have finished uploading → NOW MERGE
        if ($scope.uploadedFiles === flowObj.filesToUpload) {
          console.log('All files uploaded — starting merge phase');
          startMergePhase(ip, flowObj);
        }
      });

      //---------------------------------------------------------
      // MERGE PHASE — true final completion
      //---------------------------------------------------------
      function startMergePhase(ip, flowObj) {
        const files = flowObj.files;
        let mergesRemaining = files.length;

        console.log('Merging ' + mergesRemaining + ' files...');
        files.forEach((file) => {
          if (file.mergeCompleted === false) {
            const path = flowObj.opts.query.destination + file.relativePath;
            mergeFile(ip, path)
              .then(() => {
                file.mergeCompleted = true;
              })
              .catch((error) => {
                file.isError = true;
                file.errorMessage = `Merge failed: ${error.status} ${error.statusText}`;
                file.progress = () => 0;
                file.mergeCompleted = false;
              })
              .finally(() => {
                mergesRemaining--;

                if (mergesRemaining === 0) {
                  finalizeUpload(ip, flowObj, files);
                }

                $scope.$applyAsync();
              });
          } else {
            mergesRemaining--;

            if (mergesRemaining === 0) {
              finalizeUpload(ip, flowObj, files);
            }

            $scope.$applyAsync();
          }
        });
      }

      //---------------------------------------------------------
      // MERGE REQUEST FOR A SINGLE FILE
      //---------------------------------------------------------
      function mergeFile(ip, path) {
        return IP.mergeChunks({
          id: ip.id,
          path: path,
        }).$promise;
      }

      function getFailedFiles(flowObj) {
        return flowObj.files.filter((f) => f.isError);
      }

      //---------------------------------------------------------
      // FINAL COMPLETION AFTER MERGING ALL FILES
      //---------------------------------------------------------
      function finalizeUpload(ip, flowObj, files) {
        const hasError = files.some((f) => f.isError);

        vm.uploading = false;

        // Detect retry context
        const isRetry = files.length === 1 && files[0].wasRetried === true;

        if (isRetry) {
          const failed = getFailedFiles(flowObj);

          // 🟢 If THIS was the last failed file → cancel flow
          if (failed.length === 0) {
            console.log('Last file retried → resetting flow');
            flowObj.cancel();
          } else {
            console.log('Retry completed, some files still failing → do NOT cancel');
          }

          return; // important for retry
        }

        // --------------------------
        // NORMAL (batch) finalization
        // --------------------------
        if (hasError) {
          console.warn('Upload finished with ERRORS');
          flowObj.flowCompleted = false;
        } else {
          console.log('Upload + merge successfully completed');
          flowObj.flowCompleted = true;
          $scope.uploadedFiles = 0;
          flowObj.flowSize = flowObj.getSize();
          flowObj.flowFiles = files.length;
          flowObj.cancel();
        }

        $scope.updateGridArray();
      }

      // Store flow object for this IP
      $rootScope.flowObjects[ip.id] = flowObj;
    };
  }
}
