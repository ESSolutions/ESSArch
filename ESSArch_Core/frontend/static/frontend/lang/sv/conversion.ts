/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('sv', {
    CONVERSION_VIEW: {
      ADD_CONVERTER: 'Lägg till konverterare',
      CONVERTER: 'Konverterare',
      REMOVE_CONVERSION: 'Ta bort konvertering',
      RUN_CONVERSIONS: 'Kör konverteringar',
    },
    CONVERSION: 'Konvertering',
    NONE_SELECTED: 'Ingen vald',
  });
};
