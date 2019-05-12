/*@ngInject*/
export default $translateProvider => {
  $translateProvider.translations('sv', {
    IMPORT: {
      GET_SAS: 'Hämta leveransöverenskommelser',
      IMPORT: 'Import',
      IMPORT_PROFILE: 'Importera profil',
      IMPORT_PROFILE_FROM_FILE: 'Importera profil från fil',
      IMPORT_SA: 'Importera leveransöverenskommelse',
      IMPORT_SA_FROM_ARCHIVE: 'Hämta leveransöverenskommelse från arkiv',
      IMPORT_SA_FROM_FILE: 'Importera leveransöverenskommelse från fil',
      IMPORT_SA_FROM_FILE_SHORT: 'Importera SA från fil',
      IMPORT_URL: 'Import-url',
      PROFILE_EXISTS: 'Profil finns redan',
      PROFILE_EXISTS_DESC: 'Profil med samma ID finns redan. Vill du skriva över den?',
      PROFILE_IMPORTED: 'Profil: "{{name}}" har importerats. \nID: {{id}}',
      SA_EXISTS: 'Leveransöverenskommelse finns redan',
      SA_EXISTS_DESC: 'Leveransöverenskommelse med samma ID finns redan. Vill du skriva över den?',
      SA_IMPORTED: 'Leveransöverenskommelse "{{name}}" har importerats. \nID: {{id}}',
      SA_IS_PUBLISHED_CANNOT_BE_OVERWRITTEN:
        'Leveransöverenskommelse {{name}} är publicerad och kan inte skrivas över',
    },
  });
};
