/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('en', {
    KEYBOARD: {
      DESELECT_IP_AND_CLOSE_VIEWS: 'Deselect IP and close opened views',
      EXPAND_ROW: 'Expand row',
      EXPAND_STEP: 'Expand step',
      INCLUDE_IP_FOR_RECEIVE: 'Include IP for receive',
      IN_GENERAL_SELECTED_IP: 'In general when IP is selected',
      IP_LIST: 'IP list',
      KEYBORD_SHORTCUTS: 'Keyboard shortcuts',
      MOVE_SELECTION_DOWN: 'Move selection down',
      MOVE_SELECTION_UP: 'Move selection up',
      OPEN_KEYBOARD_SHORTCUT_INFO: 'Open keyboard shortcut info page',
      SEE_STEP_TASK_REPORT: 'See step/task report',
      SELECT_NEXT_IP: 'Select next IP',
      SELECT_PREVIOUS_IP: 'Select previous IP',
      STATUS_TREE_VIEW: 'Status tree view',
      STEP_PAGINATION_NEXT: 'Go to next page in pagination',
      STEP_PAGINATION_PREVIOUS: 'Go to previous page in pagination',
      VALIDATION_TABLE: 'Validation table',
      SEE_VALIDATION_REPORT: 'See validation report',
    },
  });
};
