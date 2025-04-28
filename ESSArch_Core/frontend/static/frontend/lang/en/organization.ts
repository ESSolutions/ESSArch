/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('en', {
    ORGANIZATION: {
      CHANGE_ORGANIZATION: 'Change organization',
      NO_ORGANIZATIONS: 'No organizations',
      ORGANIZATION: 'Organization',
      ORGANIZATION_CHANGED: 'Organization changed',
    },
    FORCE: 'Force',
    CHANGE_RELATED_ARCHIVES: 'Change related archives',
    CHANGE_RELATED_ARCHIVES_FORCE: 'Force related archives',
    CHANGE_RELATED_STRUCTUREUNITS: 'Change related structure units',
    CHANGE_RELATED_STRUCTUREUNITS_FORCE: 'Force related structure units',
    CHANGE_RELATED_NODES: 'Change related nodes',
    CHANGE_RELATED_NODES_FORCE: 'Force related nodes',
    CHANGE_RELATED_IPS: 'Change related informationpackages',
    CHANGE_RELATED_IPS_FORCE: 'Force related informationpackages',
    CHANGE_RELATED_AIDS: 'Change related access aids',
    CHANGE_RELATED_AIDS_FORCE: 'Force related access aids',
  });
};
