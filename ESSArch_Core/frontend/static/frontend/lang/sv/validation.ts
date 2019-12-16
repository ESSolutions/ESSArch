/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('sv', {
    VALIDATION_VIEW: {
      ADD_VALIDATOR: 'Lägg till validator',
      VALIDATOR: 'Validator',
      REMOVE_VALIDATION: 'Ta bort validering',
      RUN_VALIDATIONS: 'Kör valideringar',
    },
    VALIDATION: 'Validering',
    NONE_SELECTED: 'Ingen vald',
  });
};
