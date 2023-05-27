/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('sv', {
    IP: 'IP',
    AT_RECEPTION: 'I receptionen',
    ACCESS_WORKAREA: 'Arbetsyta åtkomst',
    ADVANCED_FILTERS_ON: 'Avancerad filtrering aktiv',
    ARCHIVAL_INSTITUTION: 'Arkivinstitution',
    ARCHIVAL_INSTITUTION_DESC: 'Arkivinstitution',
    ARCHIVIST_ORGANIZATION: 'Arkivorganisation',
    ARCHIVIST_ORGANIZATION_DESC: 'Arkivorganisation',
    CREATE_DATE: 'Skapad',
    CREATE_DATE_DESC: 'Datum för skapande av IP',
    CREATE_DATE_END: 'Event-tid end',
    CREATE_DATE_START: 'Event-tid start',
    CREATING: 'Skapas',
    DELETE_DESC: 'Radera IP',
    END_DATE: 'Slutdatum',
    END_DATE_DESC: 'Slutdatum',
    END_DATE_END: 'Slutdatum till',
    END_DATE_START: 'Slutdatum från',
    ENTRY_DATE: 'Skapad (SIP)',
    ENTRY_DATE_DESC: 'Datum för skapande av original-SIP',
    ENTRY_DATE_END: 'Skapad (SIP) till',
    ENTRY_DATE_START: 'Skapad (SIP) från',
    EVENTSDESC: 'Lista alla events för IP',
    EVENTS_DESC: 'Se events för IP',
    IP_CREATE_DATE_END: 'Skapad till',
    IP_CREATE_DATE_START: 'Skapad från',
    INGEST_WORKAREA: 'Arbetsyta mottag',
    IPSTATEDESC: 'Nuvarande tillstånd för IP',
    LABELDESC: 'IP-etikett',
    LABEL_DESC: 'IP-etikett',
    OBJECT_IDENTIFIER_VALUE: 'ID',
    OBJECT_IDENTIFIER_VALUE_DESC: 'IP-identifierare',
    OBJECT_SIZE: 'Objektstorlek',
    OBJECT_SIZE_DESC: 'Storlek på IP-objekt',
    UPLOADED: 'Uppladdad',
    PRESERVED: 'Arkiverad',
    PRESERVING: 'Arkiverar',
    REMOVEIP: 'Ta bort IP',
    RESPONSIBLE_DESC: 'Ansvarig användare för IP',
    START_DATE: 'Startdatum',
    START_DATE_DESC: 'Startdatum',
    START_DATE_END: 'Startdatum till',
    START_DATE_START: 'Startdatum från',
    STATE_DESC: 'IP-tillstånd',
    STATUS_DESC: 'IP-status',
    STEP_STATE_DESC: 'Steg-tillstånd, Slutförd/Fel',
  });
};
