/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('sv', {
    ORGANIZATION: {
      CHANGE_ORGANIZATION: 'Byt organisation',
      NO_ORGANIZATIONS: 'Inga organisationer',
      ORGANIZATION: 'Organisation',
      ORGANIZATION_CHANGED: 'Organisation bytt',
    },
    FORCE: 'Tvinga',
    CHANGE_RELATED_ARCHIVES: 'Byt även för relaterade arkiv',
    CHANGE_RELATED_ARCHIVES_FORCE: 'Tvinga även för relaterade arkiv',
    CHANGE_RELATED_STRUCTUREUNITS: 'Byt även för relaterade strukturenheter',
    CHANGE_RELATED_STRUCTUREUNITS_FORCE: 'Tvinga även för relaterade strukturenheter',
    CHANGE_RELATED_NODES: 'Byt även för relaterade noder',
    CHANGE_RELATED_NODES_FORCE: 'Tvinga även för relaterade noder',
    CHANGE_RELATED_IPS: 'Byt även för relaterade informationpaket',
    CHANGE_RELATED_IPS_FORCE: 'Tvinga även för relaterade informationpaket',
    CHANGE_RELATED_AIDS: 'Byt även för relaterade sökingångar',
    CHANGE_RELATED_AIDS_FORCE: 'Tvinga även för relaterade sökingångar',
  });
};
