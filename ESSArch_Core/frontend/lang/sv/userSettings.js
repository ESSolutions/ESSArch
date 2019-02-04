angular.module('essarch.language').config(function($translateProvider) {
  $translateProvider.translations('sv', {
    USER_SETTINGS: {
      AVAILABLE_COLUMNS: 'Tillgängliga kolumner',
      TABLE_COLUMNS: 'Tabellkolumner',
      USEROPTIONS: 'Användaralternativ',
      VISIBLE_COLUMNS: 'Synliga kolumner',
    },
    USERSETTINGS: 'Användarinställningar',
  });
});
