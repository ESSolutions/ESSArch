/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('sv', {
    CONVERSION_VIEW: {
      ADD_CONVERTER: 'Lägg till script',
      CONVERTER: 'Script',
      REMOVE_CONVERSION: 'Ta bort script',
      RUN_CONVERSIONS: 'Kör script',
    },
    CONVERSION: 'Script',
    NONE_SELECTED: 'Ingen vald',
  });
};
