/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('en', {
    ORGANIZATION: {
      CHANGE_ORGANIZATION: 'Change organization',
      NO_ORGANIZATIONS: 'No organizations',
      ORGANIZATION: 'Organization',
      ORGANIZATION_CHANGED: 'Organization changed',
    },
  });
};
