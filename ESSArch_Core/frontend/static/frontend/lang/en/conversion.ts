/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('en', {
    CONVERSION_VIEW: {
      ADD_CONVERTER: 'Add converter',
      CONVERTER: 'Converter',
      REMOVE_CONVERSION: 'Remove conversion',
      RUN_CONVERSIONS: 'Run conversions',
    },
    CONVERSION: 'Conversion',
    NONE_SELECTED: 'None selected',
  });
};
