/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('sv', {
    CONVERSION_VIEW: {
      ADD_CONVERTER: 'Lägg till åtgärd',
      CONVERTER: 'Verktyg',
      REMOVE_CONVERSION: 'Ta bort åtgärd',
      RUN_CONVERSIONS: 'Kör åtgärder',
    },
    CONVERSION: 'Åtgärd',
    NONE_SELECTED: 'Ingen vald',
  });
};
