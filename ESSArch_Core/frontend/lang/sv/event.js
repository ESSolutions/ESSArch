angular.module('essarch.language').config(function($translateProvider) {
  $translateProvider.translations('sv', {
    EVENT: {
      EVENTS: 'Event',
      ADDEVENT: 'Lägg till event',
      ERROR_MESSAGE: 'Event kunde inte bli tillagt',
      EVENTTIME: 'Event-tid',
      EVENTTYPE: 'Eventtyp',
      EVENT_ADDED: 'Event tillagt!',
      EVENT_FAILURE: 'Misslyckad',
      EVENT_SUCCESS: 'Lyckad',
      GLOBALSEARCHDESC_EVENT: 'Lista alla event som associeras med söktermen',
    },
    EVENTDATETIME: 'Event-tid',
    EVENTDATETIME_END: 'Event-tid slut',
    EVENTDATETIME_START: 'Event-tid start',
    EVENTDETAIL: 'Eventdetalj',
    EVENTOUTCOME: 'Event-resultat',
    LINKINGAGENTROLE: 'Agent',
  });
});
