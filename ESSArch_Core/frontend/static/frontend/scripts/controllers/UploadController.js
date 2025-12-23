// UploadController.js
export default function UploadController($scope, $rootScope, $timeout, UppyUploadService) {
  const vm = this;

  vm.uploading = false;
  $rootScope.isUploading = false;
  vm.files = [];
  vm.filesPerBatch = 1000;
  vm.currentBatch = 0;
  vm.totalBatches = 0;
  vm.silentRemoval = false;

  let previousBatchesBytes = 0;
  const countedFailedFiles = new Set();
  let uppy = null;

  // window._vm = vm; // DEBUG

  /* =========================================================================
     OVERALL PROGRESS STATE
  ========================================================================= */
  vm.overall = {
    totalFiles: 0,
    uploadedFiles: 0,
    failedFiles: 0,

    bytesUploaded: 0,
    bytesTotal: 0,
    percentBytes: 0,

    speedMBps: 0,
    etaSeconds: 0,
    startTime: null,
  };

  /* =========================================================================
     PROGRESS CALCULATIONS
  ========================================================================= */
  function updateBytesFromAllFiles() {
    // console.log('Updating byte progress from all files…');
    const files = uppy.getFiles();
    // console.log('All Uppy files:', files);
    let uploaded = 0;

    //const filesCompleted = files.filter((f) => f.progress?.uploadComplete && f.progress?.bytesUploaded != null);
    const filesCompleted = files.filter((f) => f.progress?.bytesUploaded != null);
    // console.log('Files completed with byte info:', filesCompleted);
    filesCompleted.forEach((f) => {
      // console.log('File progress for', f.name, ':', f.progress);
      if (!countedFailedFiles.has(f.id)) {
        uploaded += f.progress.bytesUploaded;
      }
    });

    vm.overall.bytesUploaded = previousBatchesBytes + uploaded;
    vm.overall.progress = (vm.overall.bytesUploaded / vm.overall.bytesTotal) * 100;

    const now = Date.now();
    const elapsed = (now - vm.overall.startTime) / 1000;

    const speed = vm.overall.bytesUploaded / elapsed; // bytes/sec
    if (speed > 0) {
      vm.overall.etaSeconds = (vm.overall.bytesTotal - vm.overall.bytesUploaded) / speed;
      vm.overall.speedMBps = Math.floor((speed / (1024 * 1024)) * 100) / 100;
    }
  }

  function computeBytesTotal() {
    vm.overall.bytesTotal = vm.files.reduce((sum, f) => sum + f.size, 0);
  }

  /* =========================================================================
     UPPY INITIALIZATION
  ========================================================================= */
  async function initUppy() {
    // console.log('Initializing Uppy…');

    uppy = await UppyUploadService.build({
      ip: $rootScope.ip,
      destinationPath: $rootScope.currentBrowserPath || '',
      restrictions: {
        allowDuplicates: true,
      },
      onComplete: onBatchDone,
      onError: (err) => console.error('Uppy error:', err),
    });

    vm.uppy = uppy;
    window._uppy = uppy;

    /* ----------------------------------------
       FILES ADDED TO DASHBOARD
    ----------------------------------------- */
    uppy.on('files-added', (added) => {
      const rawFiles = added.map((a) => a.data);

      rawFiles.forEach((file) => {
        const rel = file.relativePath === null ? null : file.relativePath ?? file.webkitRelativePath;
        const exists = vm.files.some(
          (f) =>
            f.name === file.name && f.size === file.size && (f.relativePath === rel || f.webkitRelativePath === rel)
        );

        if (!exists) {
          vm.files.push(file);
        }
      });

      vm.totalBatches = Math.ceil(vm.files.length / vm.filesPerBatch);
      vm.overall.totalFiles = vm.files.length;
      computeBytesTotal();
      $scope.$applyAsync();
    });

    /* ----------------------------------------
       FILE REMOVED MANUALLY FROM DASHBOARD
    ----------------------------------------- */
    uppy.on('file-removed', (file) => {
      if (vm.silentRemoval) return;

      let rel = file.data.relativePath || file.data.webkitRelativePath;

      vm.files = vm.files.filter(
        (f) =>
          !(f.name === file.name && f.size === file.size && (f.relativePath === rel || f.webkitRelativePath === rel))
      );

      vm.totalBatches = Math.ceil(vm.files.length / vm.filesPerBatch);
      vm.overall.totalFiles = vm.files.length;
      computeBytesTotal();

      $scope.$applyAsync();
    });

    /* ----------------------------------------
       FILE UPLOAD RESULT EVENTS
    ----------------------------------------- */
    uppy.on('upload-success', (file, response) => {
      vm.overall.uploadedFiles++;
      updateBytesFromAllFiles();
      if (countedFailedFiles.has(file.id)) {
        vm.overall.failedFiles--;
        countedFailedFiles.delete(file.id);
      }
      $scope.$applyAsync();
    });

    uppy.on('upload-error', (file) => {
      if (!countedFailedFiles.has(file.id)) {
        vm.overall.failedFiles++;
        countedFailedFiles.add(file.id);
        // console.log('File upload error, total failed files:', vm.overall.failedFiles, file);
        updateBytesFromAllFiles();
      }
      $scope.$applyAsync();
    });

    uppy.on('upload-progress', (file, progress) => {
      // console.log('File upload progress:', file, progress);
      updateBytesFromAllFiles();
      $scope.$applyAsync();
    });
  }

  /* =========================================================================
     clearTusStorage garbage in localStorage
  ========================================================================= */
  function clearTusStorage() {
    Object.keys(localStorage).forEach((key) => {
      if (key.startsWith('tus::')) {
        // console.log('Clearing TUS localStorage key:', key);
        localStorage.removeItem(key);
      }
    });
  }

  /* =========================================================================
     BATCH COMPLETE
  ========================================================================= */
  function onBatchDone(result) {
    // console.log('Batch done:', result);
    const batchBytes = result.successful.reduce((sum, f) => sum + f.size, 0);
    // console.log(
    //   'onBatchDone - Batch bytes counted towards total:',
    //   batchBytes,
    //   'previousBatchesBytes:',
    //   previousBatchesBytes
    // );
    previousBatchesBytes += batchBytes;

    if (result.failed.length === 0) {
      clearUppyFiles();
    }
    clearTusStorage();
    $scope.updateGridArray?.();
    $scope.$applyAsync();
  }

  /* =========================================================================
     CLEAR UPPY FILES WITHOUT TOUCHING vm.files
  ========================================================================= */
  function clearUppyFiles() {
    vm.silentRemoval = true;
    uppy.getFiles().forEach((f) => uppy.removeFile(f.id));
    setTimeout(() => (vm.silentRemoval = false), 30);
  }

  /* =========================================================================
     ADD A BATCH OF FILES INTO UPPY
  ========================================================================= */
  function addBatchToUppy(batchFiles) {
    batchFiles.forEach((file) => {
      let rel = file.webkitRelativePath || file.relativePath || file.name;
      if (!rel.endsWith(file.name)) {
        rel = rel.replace(/\/?$/, '/') + file.name;
      }

      const uniqueId = `${rel}-${Math.random().toString(36).slice(2)}`;

      uppy.addFile({
        id: uniqueId,
        name: file.name,
        data: file,
        type: file.type,
        meta: {relativePath: rel},
      });
    });
  }

  async function waitForFailedFilesResolved() {
    return new Promise((resolve) => {
      const interval = setInterval(() => {
        const failedFiles = uppy.getFiles().filter((f) => f.error);
        if (failedFiles.length === 0) {
          clearInterval(interval);
          resolve();
        }
      }, 1000);
    });
  }

  // async function waitForFailedFilesResolved() {
  //   return new Promise((resolve) => {
  //     const interval = setInterval(() => {
  //       const failedFiles = uppy.getFiles().filter((f) => f.error);
  //       if (failedFiles.length === 0) {
  //         clearInterval(interval);
  //         resolve();
  //       }
  //     }, 1000);
  //   });
  // }
  //       if (!countedFailedFiles.has(f.id)) {
  //       uploaded += f.progress.bytesUploaded;
  //     }

  function removeSuccessfulFilesOnly() {
    vm.silentRemoval = true;
    uppy.getFiles().forEach((f) => {
      if (!f.error && f.progress?.uploadComplete) {
        uppy.removeFile(f.id);
      }
    });
    setTimeout(() => (vm.silentRemoval = false), 30);
  }

  /* =========================================================================
     START FULL UPLOAD
  ========================================================================= */
  vm.startFullUpload = async function () {
    if (!vm.files.length) return console.warn('No files to upload');

    vm.uploading = true;
    $rootScope.isUploading = true;

    // Reset global counters
    vm.overall.totalFiles = vm.files.length;
    vm.overall.uploadedFiles = 0;
    vm.overall.failedFiles = 0;

    vm.overall.bytesUploaded = 0;
    vm.overall.percentBytes = 0;
    vm.overall.etaSeconds = 0;
    vm.overall.speedMBps = 0;

    previousBatchesBytes = 0;
    vm.overall.startTime = Date.now();
    countedFailedFiles.clear();

    computeBytesTotal();
    clearUppyFiles();

    for (let i = 0; i < vm.totalBatches; i++) {
      // Reset for this batch
      // clearUppyFiles();

      // Remove only successful files
      removeSuccessfulFilesOnly();

      console.log('before waitForFailedFilesResolved');
      // Wait for user to retry failed files
      await waitForFailedFilesResolved();
      console.log('after waitForFailedFilesResolved');

      vm.currentBatch = i + 1;
      const start = i * vm.filesPerBatch;
      const batchFiles = vm.files.slice(start, start + vm.filesPerBatch);

      // Add next batch
      addBatchToUppy(batchFiles);

      // Upload the batch
      await new Promise((resolve) => {
        uppy.once('complete', resolve);
        uppy.upload();
      });
    }

    vm.uploading = false;
    $rootScope.isUploading = false;
    vm.files = [];
  };

  /* =========================================================================
     WATCH DESTINATION PATH CHANGE
  ========================================================================= */
  $scope.$watch(
    () => $rootScope.currentBrowserPath,
    (newVal) => {
      if (uppy && newVal !== undefined) uppy.setDestinationPath(newVal);
    }
  );

  /* =========================================================================
     INIT
  ========================================================================= */
  $timeout(() => initUppy(), 10);
}
