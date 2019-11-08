/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('sv', {
    FILEBROWSER: {
      ENTERNEWFOLDERNAME: 'Ange namn för ny mapp',
      FILEBROWSER: 'Filhanterare',
      FOLDER_NAME: 'Namn',
      NEWFOLDER: 'Ny mapp',
    },
  });
};
