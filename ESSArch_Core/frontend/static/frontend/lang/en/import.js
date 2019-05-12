/*@ngInject*/
export default $translateProvider => {
  $translateProvider.translations('en', {
    IMPORT: {
      GET_SAS: 'Get submission agreements',
      IMPORT: 'Import',
      IMPORT_PROFILE: 'Import profile',
      IMPORT_PROFILE_FROM_FILE: 'Import profile from file',
      IMPORT_SA: 'Import submission agreement',
      IMPORT_SA_FROM_ARCHIVE: 'Import submission agreement from archive',
      IMPORT_SA_FROM_FILE: 'Import submission agreement from file',
      IMPORT_SA_FROM_FILE_SHORT: 'Import SA from file',
      IMPORT_URL: 'Import URL',
      PROFILE_EXISTS: 'Profile exists',
      PROFILE_EXISTS_DESC: 'Profile with same ID already exists. Would you like to overwrite it?',
      PROFILE_IMPORTED: 'Profile: "{{name}}" has been imported. \nID: {{id}}',
      SA_EXISTS: 'Submission agreement exists',
      SA_EXISTS_DESC: 'Submission agreement with same ID already exists. Would you like to overwrite it?',
      SA_IMPORTED: 'Submission agreement "{{name}}" has been imported. \nID: {{id}}',
      SA_IS_PUBLISHED_CANNOT_BE_OVERWRITTEN: 'Submission Agreement {{name}} is Published and can not be overwritten',
    },
  });
};
