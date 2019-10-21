/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('en', {
    UPLOAD: {
      CHOOSEFILES: 'Choose files',
      CHOOSEFOLDER: 'Choose folder',
      COMPLETED: 'Completed',
      COMPLETEDUPLOADING: 'Complete upload',
      DRAGANDDROPFILEHERE: 'Drag and drop your file here',
      FILES: 'File(s)',
      NO_PERMISSION_UPLOAD: 'You do not have permission to upload files to this IP',
      PAUSE: 'Pause',
      PROGRESS: 'Progress',
      TRANSFERS: 'Transfers',
      UPLOAD: 'Upload',
      UPLOADED: 'Uploaded',
      UPLOAD_COMPLETE: 'Upload complete',
    },
    PAUSED: 'Paused',
    RESUME: 'Resume',
    ISUPLOADING: 'Is uploading',
    TOTALSIZE: 'Total size',
    UPLOADFILE: 'Upload file',
    UPLOADFOLDER: 'Upload folder',
    UPLOADING: 'Uploading',
  });
};
