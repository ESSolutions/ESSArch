angular.module('essarch.language').config(function($translateProvider) {
  $translateProvider.translations('sv', {
    STATE_TREE: {
      ARGUMENTS: 'Argument',
      COPYTRACEBACK: 'Kopiera traceback',
      DURATION: 'Varaktighet',
      RUNNING: 'Körs',
      VALIDATIONS: 'Valideringar',
    },
  });
});
