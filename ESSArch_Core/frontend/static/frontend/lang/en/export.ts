/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('en', {
    EXPORT: {
      EXPORT: 'Export',
      EXPORT_AS_JSON: 'Export as JSON',
      EXPORT_PROFILE: 'Export profile',
      EXPORT_SUBMISSION_AGREEMENT: 'Export submission agreement',
    },
  });
};
