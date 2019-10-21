/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('en', {
    EVENT: {
      EVENTS: 'Events',
      ADDEVENT: 'Add event',
      CREATE_EVENT: 'Create event',
      DO_YOU_WANT_TO_REMOVE_EVENT: 'Do you want to remove event?',
      EDIT_EVENT: 'Edit event',
      ERROR_MESSAGE: 'Event could not be added',
      EVENT_LABEL: 'Event',
      EVENTTIME: 'Create date',
      EVENTTYPE: 'Event type',
      EVENT_ADDED: 'Event Added!',
      EVENT_FAILURE: 'Failure',
      EVENT_SUCCESS: 'Success',
      GLOBALSEARCHDESC_EVENT: 'List all events associated to the search term',
      REGISTERED: 'Registered',
    },
    EVENTDATETIME: 'Create date',
    EVENTDATETIME_END: 'Event create date end',
    EVENTDATETIME_START: 'Event create date start',
    EVENTDETAIL: 'Event detail',
    EVENTOUTCOME: 'Outcome',
    LINKINGAGENTROLE: 'Agent',
  });
};
