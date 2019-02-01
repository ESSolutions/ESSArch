angular.module('essarch.services').factory('ContextMenuBase', function($translate) {
  var service = {
    changeOrganization: function(callback) {
      return {
        text: $translate.instant('ORGANIZATION.CHANGE_ORGANIZATION'),
        click: function($itemScope, $event, modelValue, text, $li) {
          callback();
        },
      };
    },
  };
  return service;
});
