/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('en', {
    FILEBROWSER: {
      ENTERNEWFOLDERNAME: 'Enter new folder name',
      FILEBROWSER: 'File browser',
      FOLDER_NAME: 'Name',
      NEWFOLDER: 'New folder',
    },
  });
};
