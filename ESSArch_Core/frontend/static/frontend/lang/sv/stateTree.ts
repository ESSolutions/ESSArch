/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('sv', {
    STATE_TREE: {
      ARGUMENTS: 'Argument',
      COPYTRACEBACK: 'Kopiera traceback',
      DURATION: 'Varaktighet',
      RUNNING: 'Körs',
      VALIDATIONS: 'Valideringar',
      REPRESENTATION: 'Representation',
    },
  });
};
