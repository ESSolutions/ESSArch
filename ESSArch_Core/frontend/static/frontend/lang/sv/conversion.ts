/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('sv', {
    CONVERSION_VIEW: {
      ADD_CONVERTER: 'Lägg till åtgärd',
      CONVERTER: 'Verktyg',
      REMOVE_CONVERSION: 'Ta bort åtgärd',
      RUN_CONVERSIONS: 'Kör åtgärder',
      ADD_TO_LIST: 'Lägg till lista',
      SAVE_WORKFLOW: 'Spara',
      SAVE_AS_WORKFLOW: 'Spara som...',
      FETCH_WORKFLOW: 'Hämta arbetsflöde',
      DETAILS: 'Se detaljer',
      ACTION_DETAILS: 'Detaljer om arbetsflöde',
      SAVE_WORKFLOW_DETAILS: 'Spara arbetsflöde',
      RUN_PRESET_WORKFLOW: 'Kör förinställt arbetsflöde',
      SELECT_WORKFLOW: 'Välj arbetsflöde',
      CANCEL: 'Avbryt',
      NEW: 'Ny',
      ERROR_GET_PROFILES: 'Fel när profiler hämtas. Meddelande från server:',
      ERROR_GET_ACTION_TOOLS: 'Fel när verktyg hämtas. Meddelande från server:',
      ERROR_POST_WORKFLOW: 'Fel när arbetsflöde sparas. Meddelande från server:',
      ERROR_PUT_WORKFLOW: 'Fel när uppdatering av arbetsflöde sparas. Meddelande från server:',
      ERROR_RUN_ACTIONS: "Fel när verktyg ska köras. Felmeddelande från server:",
    },
    CONVERSION: 'Åtgärd',
    NONE_SELECTED: 'Ingen vald',
    PROFILE: 'Profil',
    TOOL_DESCRIPTION: 'Verktygsbeskrivning',
    VALIDATION_DESCRIPTION: 'Valideringsbeskrivning',
    SELECT_PROFILE: 'Välj profil',
  });
};
