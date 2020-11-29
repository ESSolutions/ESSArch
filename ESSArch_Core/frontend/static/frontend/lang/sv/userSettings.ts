/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('sv', {
    USER_SETTINGS: {
      AVAILABLE_COLUMNS: 'Tillgängliga kolumner',
      TABLE_COLUMNS: 'Tabellkolumner',
      USEROPTIONS: 'Användaralternativ',
      VISIBLE_COLUMNS: 'Synliga kolumner',
      SAVED: 'Inställning sparad',
      SAVE_ERROR: 'Det gick inte att spara intställningarna'
    },
    USERSETTINGS: 'Användarinställningar',

  });
};
