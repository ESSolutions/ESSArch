/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('en', {
    STATE_TREE: {
      ARGUMENTS: 'Arguments',
      COPYTRACEBACK: 'Copy traceback',
      DURATION: 'Duration',
      RUNNING: 'Running',
      VALIDATIONS: 'Validations',
      REPRESENTATION: 'Representation',
    },
  });
};
