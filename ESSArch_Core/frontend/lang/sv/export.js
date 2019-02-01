angular.module('essarch.language').config(function($translateProvider) {
  $translateProvider.translations('sv', {
    EXPORT: {
      EXPORT: 'Export',
      EXPORT_AS_JSON: 'Exportera som JSON',
      EXPORT_PROFILE: 'Exportera profil',
      EXPORT_SUBMISSION_AGREEMENT: 'Exportera leveransöverenskollelse',
    },
  });
});
