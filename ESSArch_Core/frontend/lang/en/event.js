angular.module('essarch.language').config(function($translateProvider) {
  $translateProvider.translations('en', {
    EVENT: {
      EVENTS: 'Events',
      ADDEVENT: 'Add event',
      CREATE_EVENT: 'Create event',
      DO_YOU_WANT_TO_REMOVE_EVENT: 'Do you want to remove event?',
      EDIT_EVENT: 'Edit event',
      ERROR_MESSAGE: 'Event could not be added',
      EVENTTIME: 'Event time',
      EVENTTYPE: 'Event type',
      EVENT_ADDED: 'Event Added!',
      EVENT_FAILURE: 'Failure',
      EVENT_SUCCESS: 'Success',
      GLOBALSEARCHDESC_EVENT: 'List all events associated to the search term',
    },
    EVENTDATETIME: 'Event time',
    EVENTDATETIME_END: 'Event time end',
    EVENTDATETIME_START: 'Event time start',
    EVENTDETAIL: 'Event detail',
    EVENTOUTCOME: 'Event outcome',
    LINKINGAGENTROLE: 'Agent',
  });
});
