angular.module('essarch.language').config(function($translateProvider) {
  $translateProvider.translations('en', {
    DASHBOARD: {
      APPRAISALS: 'Appraisals',
      ARCHIVAL_DESCRIPTION: 'Archival description',
      ORDERED_INFORMATION_PACKAGES: 'Ordered dissemination packages',
      PERMISSIONS: 'Permissions',
      ROLES: 'Roles',
      SYSTEM: 'System',
      TOTAL_OBJECT_SIZE: 'Total size',
      USERS: 'Users',
      USERS_AND_PERMISSIONS: 'Users and permissions'
    },
  });
});
