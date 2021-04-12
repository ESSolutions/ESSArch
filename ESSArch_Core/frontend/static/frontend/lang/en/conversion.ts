/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('en', {
    CONVERSION_VIEW: {
      ADD_CONVERTER: 'Add action',
      CONVERTER: 'Tools',
      REMOVE_CONVERSION: 'Remove action',
      RUN_CONVERSIONS: 'Run actions',
      ADD_TO_LIST: 'Add to list',
      SAVE_WORKFLOW: 'Save',
      SAVE_AS_WORKFLOW: 'Save as...',
      FETCH_WORKFLOW: 'Fetch workflow',
      DETAILS: 'View details',
      ACTION_DETAILS: 'Action Details',
      SAVE_WORKFLOW_DETAILS: 'Save Workflow Details',
      RUN_PRESET_WORKFLOW: 'Run preset workflow',
      SELECT_WORKFLOW: 'Select workflow',
    },
    CONVERSION: 'Actions',
    NONE_SELECTED: 'None selected',
    PROFILE: 'Profile',
    TOOL_DESCRIPTION: 'Tool description',
    VALIDATION_DESCRIPTION: 'Validation description',
    SELECT_PROFILE: 'Select profile',
  });
};
