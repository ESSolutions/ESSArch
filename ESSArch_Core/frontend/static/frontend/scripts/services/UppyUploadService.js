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

  /**
   * Create an Uppy uploader instance.
   * @param {Object} options
   * @param {Object} options.ip - The IP object containing the id
   * @param {string} options.destinationPath - Where files should be uploaded
   * @returns {Uppy.Uppy} uppy instance
   */
  service.build = function ({ip, destinationPath, onProgress, onComplete, onError}) {
    // const frozenDest = destinationPath || '';
    const csrftoken = $cookies.get('csrftoken');

    const state = {
      destinationPath: destinationPath || '',
    };

    function uppyLocale(lang) {
      switch (lang) {
        case 'sv':
          return sv_SE;
        default:
          return en_US;
      }
    }

    const uppy = new Uppy({
      autoProceed: false,
      allowMultipleUploads: true,
      restrictions: {
        maxNumberOfFiles: 100000,
      },
      locale: uppyLocale($translate.use()),
      // allowedMetaFields: ['filename', 'destination'],
      // allowedMetaFields: ['filename', 'destination', 'ip_id'],
    });

    // Expose a setter so the controller can change it dynamically
    uppy.setDestinationPath = function (newPath) {
      state.destinationPath = newPath || '';
    };

    let ip_type = 'ip';
    if ($state.includes('**.workarea.**')) {
      ip_type = 'workarea';
      console.log('in workarea');
    }
    console.log('ip_type:', ip_type);
    console.log('$state:', $state);
    console.log('$rootScope', $rootScope);
    let frozenDestination = null;

    uppy.on('file-added', (file) => {
      uppy.setFileMeta(file.id, {
        filename: file.name.replace(/[\/\\]/g, ''),
        ip_type: ip_type,
        ip_id: ip.id,
        user_id: $rootScope.auth.id,
        destination: state.destinationPath,
      });
    });

    uppy.on('upload-progress', (file, progress) => {
      if (onProgress) {
        const state = uppy.getState();
        onProgress({
          totalFiles: state.totalProgress,
          // totalComplete: state.successful.length,
          // totalError: state.failed.length,
        });
      }
    });

    uppy.on('complete', (result) => {
      if (onComplete) onComplete(result);
    });

    uppy.on('error', (err) => {
      if (onError) onError(err);
    });

    // dashboard plugin
    uppy.use(Dashboard, {
      inline: true,
      target: '#uppy-dashboard',
      height: 350,
      showProgressDetails: true,
      fileManagerSelectionType: 'both',
      // note: 'Upload up to 50,000 files including folders',
    });

    // uppy.on('*', console.log);
    // uppy.on('file-added', (f) => console.log('ADDED', f.meta));
    // uppy.on('upload', () => console.log('UPLOAD START'));
    // uppy.on('upload-started', (f) => console.log('UPLOAD STARTED FOR FILE', f.name));
    // uppy.on('plugin-used', (plugin) => console.log('PLUGIN USED:', plugin.id));

    uppy.use(Tus, {
      endpoint: `/tus/`, // POST location
      chunkSize: 50 * 1024 * 1024, // 50MB chunks (optional)
      retryDelays: [0, 1000, 3000, 5000],
      storeUrls: true,
      headers: {
        'X-CSRFToken': csrftoken,
      },
      getMeta(file) {
        console.log('getMeta in uppy tus', ip.id);
        return {
          filename: file.name,
          ip_id: ip.id,
          destination: state.destinationPath || '', // same as old "path"
        };
      },
    });

    uppy.on('retry', (file) => {
      uppy.setFileState(file.id, {
        error: null,
        backendStatus: null,
        backendErrorMessage: null,
        progress: {uploadComplete: false, uploadStarted: false},
      });
    });

    async function pollTusStatus(uploadId, file) {
      try {
        const res = await fetch(`/tus/${uploadId}/status/`);
        const json = await res.json();

        if (json.status === 'DONE') {
          // Mark the file as successfully processed
          uppy.setFileState(file.id, {
            backendStatus: 'done',
            error: null,
            backendErrorMessage: null,
            progress: {uploadComplete: true, uploadStarted: true},
          });
          // Force progress update
          uppy.emit('upload-progress', file, file.progress);
          return;
        }

        if (json.status === 'ERROR') {
          const msg = `Processing failed: ${json.error}`;

          // Mark the file as failed
          uppy.setFileState(file.id, {
            backendStatus: 'error',
            backendErrorMessage: msg,
            error: msg,
            progress: {uploadComplete: false, uploadStarted: false},
          });

          // Force progress update
          uppy.emit('upload-progress', file, file.progress);

          // Emit Uppy error for UI
          uppy.emit('upload-error', file, new Error(msg));
          return;
        }

        // Still processing → poll again after delay
        setTimeout(() => pollTusStatus(uploadId, file), 1500);
      } catch (e) {
        uppy.info('Status polling failed', 'error');
        console.error('Status polling failed', e);
      }
    }

    uppy.on('upload-success', (file, response) => {
      const uploadURL = response.uploadURL;
      const uploadId = uploadURL.split('/').pop();
      pollTusStatus(uploadId, file);
    });

    return uppy;
  };

  return service;
}
