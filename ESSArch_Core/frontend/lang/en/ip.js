angular.module('essarch.language').config(function($translateProvider) {
  $translateProvider.translations('en', {
    IP: 'IP',
    ADVANCED_FILTERS_ON: 'Advanced filter active',
    ARCHIVAL_INSTITUTION: 'Archival Institution',
    ARCHIVAL_INSTITUTION_DESC: 'Archival institution',
    ARCHIVIST_ORGANIZATION: 'Archivist organization',
    ARCHIVIST_ORGANIZATION_DESC: 'Archivist organization',
    CREATE_DATE: 'Create date',
    CREATE_DATE_DESC: 'Date of IP creation',
    CREATE_DATE_END: 'Event time end',
    CREATE_DATE_START: 'Event time start',
    DELETE_DESC: 'Delete IP',
    END_DATE: 'End date',
    END_DATE_DESC: 'End date',
    ENTRY_DATE: 'Entry date',
    ENTRY_DATE_DESC: 'Date of creation of original SIP',
    EVENTSDESC: 'List Events for IP',
    EVENTS_DESC: 'See events for IP',
    IPSTATEDESC: 'Current state of IP',
    LABELDESC: 'IP label',
    LABEL_DESC: 'IP label',
    OBJECT_IDENTIFIER_VALUE: 'ID',
    OBJECT_IDENTIFIER_VALUE_DESC: 'IP identifier',
    OBJECT_SIZE: 'Object size',
    OBJECT_SIZE_DESC: 'Size of IP object',
    REMOVEIP: 'Remove IP',
    RESPONSIBLE_DESC: 'Responsible user for IP',
    START_DATE: 'Start date',
    START_DATE_DESC: 'Start date',
    STATE_DESC: 'IP state',
    STATUS_DESC: 'IP status',
    STEP_STATE_DESC: 'Step state, Success/Failure',
  });
});
