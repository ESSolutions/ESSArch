/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('en', {
    USER_SETTINGS: {
      AVAILABLE_COLUMNS: 'Available columns',
      TABLE_COLUMNS: 'Table columns',
      USEROPTIONS: 'User options',
      VISIBLE_COLUMNS: 'Visible columns',
      SAVED: 'Settings saved',
      SAVE_ERROR: 'Error when saving settings',
    },
    USERSETTINGS: 'User settings',
  });
};
