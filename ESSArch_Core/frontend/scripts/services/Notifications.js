angular.module('essarch.services').factory('Notifications', function ($rootScope, $q, appConfig, $http, $window, $websocket) {
    // Keep all pending requests here until they get responses
    var callbacks = {};
    // Create a unique callback ID to map requests to responses
    var currentCallbackId = 0;
    // Create our websocket object with the address to the websocket
    var ws = $websocket(appConfig.webSocketProtocol + "://" + $window.location.host + "/ws/", null, { reconnectIfNotNormalClose: true });

    ws.onOpen(function () {
        $rootScope.useWebsocket = true;
    });

    ws.onClose(function () {
        $rootScope.useWebsocket = false;
    });

    ws.onMessage(function (message) {
        listener(message.data);
    });

    function listener(data) {
        var messageObj = JSON.parse(data);
        $rootScope.$broadcast('add_unseen_notification', {
            id: messageObj.id,
            message: messageObj.message,
            level: messageObj.level,
            time: 10000,
            count: messageObj.unseen_count
        });
        if(messageObj.refresh) {
            $rootScope.$broadcast('REFRESH_LIST_VIEW', {});
        }
        // If an object exists with callback_id in our callbacks object, resolve it
        if (callbacks.hasOwnProperty(messageObj.callback_id)) {
            $rootScope.$apply(callbacks[messageObj.callback_id].cb.resolve(messageObj.data));
            delete callbacks[messageObj.callbackID];
        }
    }

    // This creates a new callback ID for a request
    function getCallbackId() {
        currentCallbackId += 1;
        if (currentCallbackId > 10000) {
            currentCallbackId = 0;
        }
        return currentCallbackId;
    }
    var service = {
        /**
         * Add notification
         * @param message - Message to show on the the alert
         * @param level - level of alert, applies a class to the alert
         * @param time - Adds a duration to the alert
         */
        add: function(message, level, time, options) {
            $rootScope.$broadcast('add_notification', { message: message, level: level, time: time, options: options});
        },
        /**
         * Show alert
         */
        show: function() {
            $rootScope.$broadcast('show_notifications', {});
        },
        /**
         * Hide notifications
         */
        hide: function() {
            $rootScope.$broadcast('hide_notifications', {});
        },
        toggle: function() {
            $rootScope.$broadcast('toggle_notifications', {});

        },
        getNotifications: function(pageSize) {
            return $http.get(appConfig.djangoUrl + "notifications/", {params: {page_size: pageSize}}).then(function(response) {
                return response.data;
            })
        },
        getNextPage: function(pageSize, id) {
            return $http.get(appConfig.djangoUrl + "notifications/", {params: {page_size: pageSize, after: id, after_field: 'id'}}).then(function(response) {
                return {
                    data: response.data,
                    count: response.headers('Count')
                };
            }).catch(function(response) {
                return [];
            })
        },
        getNextNotification: function() {
            return $http.get(appConfig.djangoUrl + "notifications/", {params: {page_size: 1, page: 7}}).then(function(response) {
                return response.data;
            })
        },
        getUnseenNotifications: function(date) {
            return $http.get(appConfig.djangoUrl + "notifications/", {params: {create_date: date}}).then(function(response) {
                return response.data;
            })
        },
        delete: function(id) {
            return $http.delete(appConfig.djangoUrl + "notifications/" + id + "/").then(function(response) {
                return response;
            })
        },
        deleteAll: function() {
            return $http.delete(appConfig.djangoUrl + "notifications/").then(function(response) {
                return response;
            })
        }
    }
    return service;
});
