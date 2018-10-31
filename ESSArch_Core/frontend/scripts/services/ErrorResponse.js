angular.module('essarch.services').factory('ErrorResponse', function($translate, Notifications) {
    var service = {
        /**
         * Avoids double error messages and show translated unknown error when no message from server
         * @param {Object} response Request error response
         */
        default: function(response) {
            if(![401, 403, 500, 503].includes(response.status)) {
                if(response.data && response.data.detail) {
                    Notifications.add(response.data.detail, "error");
                } else {
                    Notifications.add($translate('UNKNOWN_ERROR'), 'error')
                }
            }
        }
    }
    return service;
})
