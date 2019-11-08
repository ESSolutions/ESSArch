/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('sv', {
    USER_SETTINGS: {
      AVAILABLE_COLUMNS: 'Tillgängliga kolumner',
      TABLE_COLUMNS: 'Tabellkolumner',
      USEROPTIONS: 'Användaralternativ',
      VISIBLE_COLUMNS: 'Synliga kolumner',
    },
    USERSETTINGS: 'Användarinställningar',
  });
};
