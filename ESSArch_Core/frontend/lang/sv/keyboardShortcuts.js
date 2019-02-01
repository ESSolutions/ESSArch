angular.module('essarch.language').config(function($translateProvider) {
  $translateProvider.translations('sv', {
    KEYBOARD: {
      DESELECT_IP_AND_CLOSE_VIEWS: 'Avmarkera valt IP ochstäng öppnade vyer',
      EXPAND_ROW: 'Expandera rad',
      EXPAND_STEP: 'Expandera steg',
      INCLUDE_IP_FOR_RECEIVE: 'Inkludera IP för att ta emot',
      IN_GENERAL_SELECTED_IP: 'Generellt när ett IP är valt',
      IP_LIST: 'IP-lista',
      KEYBORD_SHORTCUTS: 'Tangentbordsgenvägar',
      MOVE_SELECTION_DOWN: 'Flytta merkering nedåt',
      MOVE_SELECTION_UP: 'Flytta markering uppåt',
      OPEN_KEYBOARD_SHORTCUT_INFO: 'Öppna tangentbordsgenväg-sida',
      SEE_STEP_TASK_REPORT: 'Se steg/jobb-rapport',
      SELECT_NEXT_IP: 'Välj nästa IP',
      SELECT_PREVIOUS_IP: 'Välj föregående IP',
      STATUS_TREE_VIEW: 'Status-träd-vy',
      STEP_PAGINATION_NEXT: 'Gå till nästa sida i paginering',
      STEP_PAGINATION_PREVIOUS: 'Gå till föregående sida i paginering',
      VALIDATION_TABLE: 'Valideringslista',
      SEE_VALIDATION_REPORT: 'Se valideringsrapport',
    },
  });
});
