/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('en', {
    FILEBROWSER: {
      ENTERNEWFOLDERNAME: 'Enter new folder name',
      FILEBROWSER: 'Workspace',
      FOLDER_NAME: 'Name',
      NEWFOLDER: 'New folder',
    },
  });
};
