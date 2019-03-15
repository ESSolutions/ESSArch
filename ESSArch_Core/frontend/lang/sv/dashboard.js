angular.module('essarch.language').config(function($translateProvider) {
  $translateProvider.translations('sv', {
    DASHBOARD: {
      APPRAISALS: 'Utförda gallringar',
      ARCHIVAL_DESCRIPTION: 'Arkivredovisning',
      ORDERED_INFORMATION_PACKAGES: 'Beställda utlämnandepaket',
      PERMISSIONS: 'Behörigheter',
      ROLES: 'Roller',
      SYSTEM: 'Bestånd',
      TOTAL_OBJECT_SIZE: 'Total storlek',
      USERS: 'Användare',
      USERS_AND_PERMISSIONS: 'Användare och behörigheter'
    },
  });
});
