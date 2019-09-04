/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('sv', {
    EVENT: {
      EVENTS: 'Händelser',
      ADDEVENT: 'Lägg till händelse',
      CREATE_EVENT: 'Skapa händelse',
      DO_YOU_WANT_TO_REMOVE_EVENT: 'Vill du ta bort händelse?',
      EDIT_EVENT: 'Redigera händelse',
      ERROR_MESSAGE: 'Händelse kunde inte bli tillagd',
      EVENT_LABEL: 'Händelse',
      EVENTTIME: 'Skapad',
      EVENTTYPE: 'Typ av händelse',
      EVENT_ADDED: 'Händelse tillagd!',
      EVENT_FAILURE: 'Misslyckad',
      EVENT_SUCCESS: 'Lyckad',
      GLOBALSEARCHDESC_EVENT: 'Lista alla händelser som associeras med söktermen',
      REGISTERED: 'Registrerad',
    },
    EVENTDATETIME: 'skapad',
    EVENTDATETIME_END: 'Händelse skapad slut',
    EVENTDATETIME_START: 'Händelse skapad start',
    EVENTDETAIL: 'Eventdetalj',
    EVENTOUTCOME: 'Resultat',
    LINKINGAGENTROLE: 'Agent',
  });
};
