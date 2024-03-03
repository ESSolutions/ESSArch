/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('en', {
    DASHBOARD: {
      APPRAISALS: 'Appraisals',
      ARCHIVAL_DESCRIPTION: 'Archival description',
      AUTHORITY_RECORDS: 'Authority records',
      BUILD_REPORT: 'Build report',
      DELIVERIES: 'Accessions',
      GENERATE_REPORT: 'Generate report',
      INFORMATION_PACKAGES: 'Information packages',
      INFORMATION_PACKAGES_AIP: 'Preserved Information packages',
      ORDERED_INFORMATION_PACKAGES: 'Ordered dissemination packages',
      PERMISSIONS: 'Permissions',
      ROLES: 'Roles',
      SELECT_INFORMATION_FOR_REPORT: 'Select information to be included in the report',
      SYSTEM: 'System',
      PRESERVED: 'Preserved',
      TAGS: 'Archival Descriptions',
      TOTAL_OBJECT_SIZE: 'Total size',
      AIP_OBJECT_SIZE: 'Preserved total size',
      USERS: 'Users',
      USERS_AND_PERMISSIONS: 'Users and permissions',
    },
  });
};
