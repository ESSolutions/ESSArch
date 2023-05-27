/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('en', {
    IP: 'IP',
    AT_RECEPTION: 'At reception',
    ACCESS_WORKAREA: 'Workspace access',
    ADVANCED_FILTERS_ON: 'Advanced filter active',
    ARCHIVAL_INSTITUTION: 'Archival Institution',
    ARCHIVAL_INSTITUTION_DESC: 'Archival institution',
    ARCHIVIST_ORGANIZATION: 'Archivist organization',
    ARCHIVIST_ORGANIZATION_DESC: 'Archivist organization',
    CREATE_DATE: 'Create date',
    CREATE_DATE_DESC: 'Date of IP creation',
    CREATE_DATE_END: 'Event time end',
    CREATE_DATE_START: 'Event time start',
    CREATING: 'Creating',
    DELETE_DESC: 'Delete IP',
    END_DATE: 'End date',
    END_DATE_DESC: 'End date',
    END_DATE_END: 'End date end',
    END_DATE_START: 'End date start',
    ENTRY_DATE: 'Entry date',
    ENTRY_DATE_DESC: 'Date of creation of original SIP',
    ENTRY_DATE_END: 'Entry date end',
    ENTRY_DATE_START: 'Entry date start',
    EVENTSDESC: 'List Events for IP',
    EVENTS_DESC: 'See events for IP',
    IP_CREATE_DATE_END: 'Create date end',
    IP_CREATE_DATE_START: 'Create date start',
    INGEST_WORKAREA: 'Workspace ingest',
    IPSTATEDESC: 'Current state of IP',
    LABELDESC: 'IP label',
    LABEL_DESC: 'IP label',
    OBJECT_IDENTIFIER_VALUE: 'ID',
    OBJECT_IDENTIFIER_VALUE_DESC: 'IP identifier',
    OBJECT_SIZE: 'Object size',
    OBJECT_SIZE_DESC: 'Size of IP object',
    UPLOADED: 'Uploaded',
    PRESERVED: 'Preserved',
    PRESERVING: 'Preserving',
    REMOVEIP: 'Remove IP',
    RESPONSIBLE_DESC: 'Responsible user for IP',
    START_DATE: 'Start date',
    START_DATE_DESC: 'Start date',
    START_DATE_END: 'Start date end',
    START_DATE_START: 'Start date start',
    STATE_DESC: 'IP state',
    STATUS_DESC: 'IP status',
    STEP_STATE_DESC: 'Step state, Success/Failure',
  });
};
