/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('sv', {
    EXPORT: {
      EXPORT: 'Export',
      EXPORT_AS_JSON: 'Exportera som JSON',
      EXPORT_PROFILE: 'Exportera profil',
      EXPORT_SUBMISSION_AGREEMENT: 'Exportera leveransöverenskollelse',
    },
  });
};
