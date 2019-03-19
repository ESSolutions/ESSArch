angular.module('essarch.language').config(function($translateProvider) {
  $translateProvider.translations('en', {
    DASHBOARD: {
      APPRAISALS: 'Appraisals',
      ARCHIVAL_DESCRIPTION: 'Archival description',
      BUILD_REPORT: 'Build report',
      GENERATE_REPORT: 'Generate report',
      INFORMATION_PACKAGES: 'Information packages',
      ORDERED_INFORMATION_PACKAGES: 'Ordered dissemination packages',
      PERMISSIONS: 'Permissions',
      ROLES: 'Roles',
      SELECT_INFORMATION_FOR_REPORT: 'Select information to be included in the report',
      SYSTEM: 'System',
      TAGS: 'Arkivredovisning',
      TOTAL_OBJECT_SIZE: 'Total size',
      USERS: 'Users',
      USERS_AND_PERMISSIONS: 'Users and permissions',
    },
  });
});
