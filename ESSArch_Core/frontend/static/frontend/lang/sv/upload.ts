/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('sv', {
    UPLOAD: {
      CHOOSEFILES: 'Välj filer',
      CHOOSEFOLDER: 'Välj mapp',
      COMPLETED: 'färdig',
      COMPLETEDUPLOADING: 'Slutför uppladdning',
      DRAGANDDROPFILEHERE: 'Dra och släpp filer här',
      FILES: 'Fil(er)',
      NO_PERMISSION_UPLOAD: 'Du saknar behörighet att ladda upp filer till detta IP',
      PAUSE: 'Pausa',
      PROGRESS: 'Progress',
      TRANSFERS: 'Överföringar',
      UPLOAD: 'Ladda upp',
      UPLOADED: 'Uppladdat',
      UPLOAD_COMPLETE: 'Uppladdning slutförd',
    },
    PAUSED: 'Pausad',
    RESUME: 'Återuppta',
    ISUPLOADING: 'Laddas upp',
    TOTALSIZE: 'Total storlek',
    UPLOADFILE: 'Ladda upp fil',
    UPLOADFOLDER: 'Ladda upp mapp',
    UPLOADING: 'Laddar upp',
  });
};
