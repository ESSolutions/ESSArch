angular.module('essarch.language').config(function($translateProvider) {
  $translateProvider.translations('sv', {
    EVENT: {
      EVENTS: 'Event',
      ADDEVENT: 'Lägg till event',
      CREATE_EVENT: 'Skapa event',
      DO_YOU_WANT_TO_REMOVE_EVENT: 'Vill du ta bort event?',
      EDIT_EVENT: 'Redigera event',
      ERROR_MESSAGE: 'Event kunde inte bli tillagt',
      EVENT_LABEL: 'Händelse',
      EVENTTIME: 'Event-tid',
      EVENTTYPE: 'Eventtyp',
      EVENT_ADDED: 'Event tillagt!',
      EVENT_FAILURE: 'Misslyckad',
      EVENT_SUCCESS: 'Lyckad',
      GLOBALSEARCHDESC_EVENT: 'Lista alla event som associeras med söktermen',
      REGISTERED: 'Registrerad',
    },
    EVENTDATETIME: 'Event-tid',
    EVENTDATETIME_END: 'Event-tid slut',
    EVENTDATETIME_START: 'Event-tid start',
    EVENTDETAIL: 'Eventdetalj',
    EVENTOUTCOME: 'Event-resultat',
    LINKINGAGENTROLE: 'Agent',
  });
});
