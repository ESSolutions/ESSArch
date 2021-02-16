/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('en', {
    CONVERSION_VIEW: {
      ADD_CONVERTER: 'Add action',
      CONVERTER: 'Tools',
      REMOVE_CONVERSION: 'Remove action',
      RUN_CONVERSIONS: 'Run actions',
    },
    CONVERSION: 'Actions',
    NONE_SELECTED: 'None selected',
    PROFILE: 'Profile',
    TOOL_DESCRIPTION: 'Tool description',
    VALIDATION_DESCRIPTION: 'Validation description',
    SELECT_PROFILE: 'Select profile',
  });
};
