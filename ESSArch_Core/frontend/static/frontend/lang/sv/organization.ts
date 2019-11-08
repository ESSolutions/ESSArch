/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('sv', {
    ORGANIZATION: {
      CHANGE_ORGANIZATION: 'Byt organisation',
      NO_ORGANIZATIONS: 'Inga organisationer',
      ORGANIZATION: 'Organisation',
      ORGANIZATION_CHANGED: 'Organisation bytt',
    },
  });
};
