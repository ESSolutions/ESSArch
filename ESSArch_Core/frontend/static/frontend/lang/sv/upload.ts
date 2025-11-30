/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('sv', {
    UPLOAD: {
      ACTIONS: 'Åtgärder',
      CHOOSEFILES: 'Välj filer',
      CHOOSEFOLDER: 'Välj mapp',
      COMPLETED: 'Färdiga',
      COMPLETEDUPLOADING: 'Slutför uppladdning',
      DRAGANDDROPFILEHERE: 'Dra och släpp filer här',
      FILES: 'Fil(er)',
      NO_PERMISSION_UPLOAD: 'Du saknar behörighet att ladda upp filer till detta IP',
      PAUSE: 'Pausa',
      PROGRESS: 'Progress',
      TRANSFERS: 'Överföringar',
      UPLOAD: 'Ladda upp',
      UPLOADCONTENT: 'Ladda upp innehåll',
      UPLOADED: 'Uppladdat',
      UPLOAD_COMPLETE: 'Uppladdning slutförd',
      TOTALFILES: 'Antal filer',
      FAILED: 'Fel',
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
