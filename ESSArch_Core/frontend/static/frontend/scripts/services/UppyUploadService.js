import Uppy from '@uppy/core';
import Dashboard from '@uppy/dashboard';
import Tus from '@uppy/tus';
import sv_SE from '@uppy/locales/lib/sv_SE';
import en_US from '@uppy/locales/lib/en_US';
import '@uppy/core/css/style.css';
import '@uppy/dashboard/css/style.css';

UppyUploadService.$inject = ['$cookies', '$translate', '$state', '$rootScope'];
export default function UppyUploadService($cookies, $translate, $state, $rootScope) {
  const service = {};

  service.build = function ({ip, destinationPath, onProgress, onComplete, onError}) {
    const csrftoken = $cookies.get('csrftoken');

    function locale(lang) {
      return lang === 'sv' ? sv_SE : en_US;
    }
    const state = {destinationPath: destinationPath || ''};

    const uppy = new Uppy({autoProceed: false, allowMultipleUploads: true, locale: locale($translate.use())});

    const loader = document.getElementById('uppy-loader');

    function initDragSpinner() {
      const dropArea = document.querySelector('#uppy-dashboard .uppy-Dashboard-inner');
      if (!dropArea) {
        // console.log('no dropArea');
        // Dashboard not rendered yet, try again shortly
        setTimeout(initDragSpinner, 50);
        return;
      }
      // console.log('dropArea found');

      // Show spinner when file dialog opens
      function hookDashboardPicker() {
        const dashboard = document.querySelector('#uppy-dashboard');
        if (!dashboard) {
          setTimeout(hookDashboardPicker, 50);
          return;
        }

        // Listen for clicks ONLY on the file/folder browse button
        dashboard.addEventListener(
          'click',
          (e) => {
            // Check if click is on "browse" button
            const browseButton = e.target.closest('.uppy-Dashboard-browse');
            if (browseButton) {
              // console.log('picker opened, showing loader');
              loader.style.display = 'flex';
            }
          },
          true // capture phase
        );
      }
      hookDashboardPicker();

      // Show spinner when files are dropped
      dropArea.addEventListener('drop', () => {
        // console.log('files dropped, showing loader');
        loader.style.display = 'flex';
      });

      // Hide spinner after files are added
      uppy.on('files-added', () => {
        // console.log('files added, hiding loader');
        loader.style.display = 'none';
      });
    }

    // Start checking for Dashboard DOM
    initDragSpinner();

    uppy.setDestinationPath = function (newPath) {
      state.destinationPath = newPath || '';
    };

    let ip_type = 'ip';
    if ($state.includes('**.workarea.**')) {
      ip_type = 'workarea';
      // console.log('in workarea');
    }

    uppy.on('file-added', (file) => {
      uppy.setFileMeta(file.id, {
        filename: file.name.replace(/[\/\\]/g, ''),
        ip_type: ip_type,
        ip_id: ip.id,
        user_id: $rootScope.auth.id,
        destination: state.destinationPath,
      });
    });

    uppy.on('upload-progress', () => {
      if (onProgress) onProgress();
    });
    uppy.on('complete', (result) => {
      if (onComplete) onComplete(result);
    });
    uppy.on('error', (err) => {
      if (onError) onError(err);
    });

    uppy.use(Dashboard, {
      inline: true,
      target: '#uppy-dashboard',
      width: '100%',
      height: 300,
      hideUploadButton: true,
      showProgressDetails: true,
      disableThumbnailGenerator: true,
      fileManagerSelectionType: 'both', // allow files + folders
    });

    uppy.use(Tus, {
      endpoint: '/tus/',
      chunkSize: 50 * 1024 * 1024,
      retryDelays: [0, 1000, 3000, 5000],
      limit: 10,
      storeUrls: false,
      storeFingerprintForResuming: false,
      headers: {'X-CSRFToken': csrftoken},
      getMeta(file) {
        return {
          filename: file.name,
          ip_id: ip.id,
          destination: state.destinationPath || '',
        };
      },
    });

    return uppy;
  };

  return service;
}
