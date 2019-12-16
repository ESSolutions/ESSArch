/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('en', {
    VALIDATION_VIEW: {
      ADD_VALIDATOR: 'Add validator',
      VALIDATOR: 'Validator',
      REMOVE_VALIDATION: 'Remove validation',
      RUN_VALIDATIONS: 'Run validations',
    },
    VALIDATION: 'Validation',
    NONE_SELECTED: 'None selected',
  });
};
