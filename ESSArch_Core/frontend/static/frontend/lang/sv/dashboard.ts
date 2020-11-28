/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('sv', {
    DASHBOARD: {
      APPRAISALS: 'Utförda gallringar',
      ARCHIVAL_DESCRIPTION: 'Arkivredovisning',
      AUTHORITY_RECORDS: 'Arkivbildare',
      BUILD_REPORT: 'Bygg rapport',
      DELIVERIES: 'Registrerade leveranser',
      GENERATE_REPORT: 'Generera rapport',
      INFORMATION_PACKAGES: 'Informationspaket',
      ORDERED_INFORMATION_PACKAGES: 'Beställda utlämnandepaket',
      PERMISSIONS: 'Behörigheter',
      ROLES: 'Roller',
      SELECT_INFORMATION_FOR_REPORT: 'Välj vilken information som ska inkluderas i rapporten',
      SYSTEM: 'Bestånd',
      TAGS: 'Arkivredovisning',
      TOTAL_OBJECT_SIZE: 'Total storlek',
      USERS: 'Användare',
      USERS_AND_PERMISSIONS: 'Användare och behörigheter',
    },
  });
};
