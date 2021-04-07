/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('sv', {
    CONVERSION_VIEW: {
      ADD_CONVERTER: 'Lägg till åtgärd',
      CONVERTER: 'Verktyg',
      REMOVE_CONVERSION: 'Ta bort åtgärd',
      RUN_CONVERSIONS: 'Kör åtgärder',
      ADD_TO_LIST: 'Lägg till lista',
      SAVE_WORKFLOW: 'Spara arbetsflöde',
      FETCH_WORKFLOW: 'Hämta arbetsflöde',
      DETAILS: 'Se detaljer',
      ACTION_DETAILS: 'Detaljer om arbetsflöde',
      SAVE_WORKFLOW_DETAILS: 'Spara arbetsflöde',
      RUN_PRESET_WORKFLOW: 'Kör förinställt arbetsflöde',
    },
    CONVERSION: 'Åtgärd',
    NONE_SELECTED: 'Ingen vald',
    PROFILE: 'Profil',
    TOOL_DESCRIPTION: 'Verktygsbeskrivning',
    VALIDATION_DESCRIPTION: 'Valideringsbeskrivning',
    SELECT_PROFILE: 'Välj profil',
  });
};
