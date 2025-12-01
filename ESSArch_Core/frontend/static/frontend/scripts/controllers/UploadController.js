// UploadController.js
//UploadController.$inject = ['$scope', '$rootScope', 'UppyUploadService', 'IP'];
export default function UploadController($scope, $rootScope, UppyUploadService, IP) {
  const vm = this;
  vm.uploading = false;

  vm.stats = {
    total: 0,
    completed: 0,
    failed: 0,
  };

  // console.log('$rootScope', $rootScope);
  // console.log('vm.browserstate in UploadController:', vm.browserstate);
  // console.log('Initial browser path in UploadController:', $rootScope.currentBrowserPath);
  $scope.$watch(
    () => $rootScope.currentBrowserPath,
    function (newVal) {
      if (vm.uppy && newVal !== undefined) {
        console.log('Path changed vm.uppy.setDestinationPath:', newVal);
        vm.uppy.setDestinationPath(newVal);
      }
    }
  );

  console.log('UploadController initialized');
  // console.log('$rootScope:', $rootScope);
  // console.log('Current IP:', $rootScope.ip);
  vm.initUploader = function () {
    const destination = $rootScope.currentBrowserPath || '';
    console.log('destination:', destination);

    vm.uppy = UppyUploadService.build({
      ip: $rootScope.ip,
      destinationPath: destination,

      onProgress: () => {
        const files = vm.uppy.getState().files || {};

        vm.stats.total = Object.keys(files).length;

        vm.stats.completed = Object.values(files).filter(
          (f) => f.progress?.uploadComplete && f.backendStatus !== 'error'
        ).length;

        vm.stats.failed = Object.values(files).filter((f) => f.error || f.backendStatus === 'error').length;

        $scope.$applyAsync();
      },

      onComplete: (result) => {
        console.log('onComplete', result);
        //   vm.stats.completed = result.successful.length;
        //   vm.stats.failed = result.failed.length;
        $scope.updateGridArray();
      },

      onError: (err) => {
        console.error('Upload error:', err);
        vm.uploading = false;
      },
    });

    // After initializing vm.uppy with UppyUploadService.build
    function attachDoneListener() {
      // Use MutationObserver to watch the dashboard DOM
      const dashboard = document.querySelector('#uppy-dashboard');
      if (!dashboard) return;

      const observer = new MutationObserver(() => {
        const doneBtn = dashboard.querySelector('.uppy-StatusBar-actionBtn--done');
        if (doneBtn && !doneBtn.dataset.listenerAttached) {
          doneBtn.dataset.listenerAttached = 'true'; // avoid multiple attachments
          doneBtn.addEventListener('click', () => {
            console.log('Done button clicked!');
            Object.values(vm.uppy.getState().files).forEach((file) => vm.uppy.removeFile(file.id));
            vm.stats.total = 0;
            vm.stats.completed = 0;
            vm.stats.failed = 0;
            $scope.$applyAsync();
          });
        }
      });

      observer.observe(dashboard, {childList: true, subtree: true});
    }

    // Call after vm.uppy is initialized
    attachDoneListener();
  };

  vm.initUploader();
}
