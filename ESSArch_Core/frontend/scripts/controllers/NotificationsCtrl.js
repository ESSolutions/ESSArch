angular.module('essarch.controllers').controller('NotificationsCtrl', function(appConfig, Notifications, $timeout, $interval, $scope, $rootScope, $http, $window, Messenger, $state, $translate) {
    var vm = this;
    vm.visible = false;
    vm.alerts = [];
    vm.frontendAlerts = [];
    vm.backendAlerts = [];
    var interval;
    vm.$onInit = function () {
        vm.notificationsEnabled = $rootScope.auth.notifications_enabled;
        Messenger.options = {
            extraClasses: 'messenger-fixed messenger-on-bottom messenger-on-right',
            theme: 'flat'
        }
        vm.updateUnseen();
        if(!$rootScope.useWebsocket) {
            interval = $interval(function() {
                vm.getNotifications();
                vm.updateUnseen();
            }, appConfig.notificationInterval)
        }
    }

    $scope.$watch(function () { return $rootScope.useWebsocket }, function (newValue, oldValue) {
        if (newValue != oldValue) {
            if ($rootScope.useWebsocket) {
                $interval.cancel(interval);
            } else {
                interval = $interval(function () {
                    vm.getNotifications();
                    vm.updateUnseen();
                }, appConfig.notificationInterval)
            }
        }
    })

    vm.getNotifications = function(show) {
        if(angular.isUndefined(show)) {
            show = true;
        }
        vm.nextPageLoading = true;
        var pageSize = Math.ceil(($(window).height() * 0.6) / 38)+2;
        return Notifications.getNotifications(pageSize).then(function(data) {
            vm.nextPageLoading = false;
            vm.backendAlerts = data;
            vm.alerts = vm.backendAlerts;
            return vm.alerts;
        });
    }

    vm.updateEnabledStatus = function(val) {
        return $http({
            method: 'PATCH',
            url: appConfig.djangoUrl+"me/",
            data: {
                notifications_enabled: val
            }
        }).then(function(response) {
            $rootScope.auth = response.data;
            vm.notificationsEnabled = response.data.notifications_enabled;
            return response;
        })
    }

    vm.updateUnseen = function(count) {
        if(count) {
            $rootScope.unseenNotifications = count;
        } else {
            $http.head(appConfig.djangoUrl + "notifications/", {params: { seen: false }}).then(function(response) {
                $rootScope.unseenNotifications = response.headers().count;
            });
        }
    }

    vm.showAlert = function() {
        vm.visible = true;
        Messenger().hideAll();
        vm.getNotifications();
        vm.setAllSeen();
    }

    vm.setSeen = function(alerts) {
        alerts.forEach(function(alert) {
            if(alert.id && !alert.seen) {
                $http({
                    method: 'PATCH',
                    url: appConfig.djangoUrl + 'notifications/' + alert.id + '/',
                    data: { seen: true }
                }).then(function(response) {
                    alert.seen = true;
                    if($rootScope.unseenNotifications > 0) {
                        $rootScope.unseenNotifications -= 1;
                    }
                }).catch(function(response) {});
            } else if(!alert.id) {
                alert.seen = true;
            }
        });
    }

    vm.setAllSeen = function() {
        $http({
            method: 'POST',
            url: appConfig.djangoUrl + 'notifications/set-all-seen/',
        }).then(function(response) {
            vm.updateUnseen(0);
        }).catch(function(response) {});
    }

    vm.hideAlert = function() {
        vm.visible = false;
        $window.onclick = null;
        vm.setAllSeen();
    }

    vm.removeAlert = function (alert, index) {
        Notifications.delete(alert.id).then(function (response) {
            vm.backendAlerts.splice(index, 1);
            vm.alerts = vm.backendAlerts;
        });
    }

    function getNext() {
        return Notifications.getNextNotification().then(function(data) {
            vm.backendAlerts.push(data[0]);
            vm.alerts = vm.backendAlerts;
            if(!vm.alerts.length == 0) {
                vm.visible = false;
            }
            return vm.alerts;
        }).catch(function(response) {
            if(!vm.alerts.length == 0) {
                vm.visible = false;
            }
            return vm.alerts;
        })
    }
    vm.clearAll = function() {
        Notifications.deleteAll().then(function(response) {
            vm.visible = false;
            vm.alerts = [];
            vm.backendAlerts = [];
            vm.frontendAlerts = [];
            vm.updateUnseen();
        })
    }
    vm.nextPage = function () {
        if(!vm.nextPageLoading) {
            vm.nextPageLoading = true;
            Notifications.getNextPage(10, vm.alerts[vm.alerts.length-1].id).then(function(response) {
                vm.nextPageLoading = false;
                response.data.forEach(function(x) {
                    vm.backendAlerts.push(x);
                });
                vm.alerts = vm.backendAlerts;
            })
        }
    }

    /**
     * Add notifications
     * @param message - Message to show on the the alert
     * @param level - level of alert, applies a class to the alert
     * @param time - Adds a duration to the alert
     */

    vm.addAlert = function (id, message, level, time, options) {
        var alert = {message: message, level: level, time_created: new Date()};
        if(id) {
            alert.id = id;
            vm.backendAlerts.unshift(alert);
        } else {
            vm.frontendAlerts.unshift(alert);
        }
        if(vm.notificationsEnabled) {
            var actions = (!angular.isUndefined(options.actions) && options.actions !== null) ? options.actions:null;
            var post = {
                message: message,
                type: level,
                hideAfter: time?time/1000:10,
                showCloseButton: true,
                onClickClose: function() {
                    vm.setSeen([{id: id}]);
                },
                actions: actions
            };
            Messenger().post(post);
        }
    }
    vm.toggleAlert = function () {
        if (vm.visible) {
            vm.hideAlert();
        } else {
            vm.showAlert();
            $window.onclick = function (event) {
                var clickedElement = $(event.target);
                if (!clickedElement) return;
                var elementClasses = event.target.classList;
                var clickedOnAlertIcon = elementClasses.contains('fa-bell') ||
                elementClasses.contains('top-alert-container') ||
                elementClasses.contains('top-alert-container') ||
                clickedElement.parents('.top-alert-container').length
                if (!clickedOnAlertIcon) {
                    vm.hideAlert();
                    $scope.$apply();
                }
            }
        }
    }

    $rootScope.disconnectedAlert = null;
    $rootScope.$on('disconnected', function (event, data) {
        if(!$rootScope.disconnected) {
            $rootScope.disconnected = true;
            $rootScope.disconnectedAlert = Messenger().post({
                message: data.detail,
                type: "error",
                hideAfter: null,
                actions: {
                    retry: {
                        label: $translate.instant('RETRY'),
                        action: function() {
                            $http.head(appConfig.djangoUrl+"me/").then(function(response) {
                                $rootScope.disconnected = null;
                                $rootScope.$broadcast('reconnected', {detail: $translate.instant("CONNECTION_RESTORED")});
                            }).catch(function() {
                            })
                        }
                    }
                }
            })
        }
    });
    $rootScope.$on('reconnected', function (event, data) {
        $rootScope.disconnected = false;
        $rootScope.disconnectedAlert.update({
            message: data.detail,
            type: "success",
            showCloseButton: true,
            hideAfter: 10,
            actions: null
        })
    })

    // Listen for show/hide events
    $scope.$on('add_notification', function (event, data, actions) {
        vm.addAlert(data.id, data.message, data.level, data.time, data.options);
    });
    $scope.$on('add_unseen_notification', function (event, data) {
        vm.updateUnseen(data.count);
        vm.addAlert(data.id, data.message, data.level, data.time, false);
        if(vm.showAlerts) {
            vm.setSeen(vm.alerts.slice(0,5));
        }
    });
    $scope.$on('show_notification', function (event, data) {
        if(vm.alerts.length > 0) {
            vm.showAlert();
            $timeout(function() {
                vm.showAlerts = true;
                vm.setSeen(vm.alerts.slice(0, 5));
            }, 300);
        }
    });
    $scope.$on('toggle_notifications', function (event, data) {
        vm.toggleAlert();
    });
    $scope.$on('hide_notifications', function (event, data) {
        vm.hideAlert();
    });
    $scope.$on('get_notifications', function (event, data) {
        vm.getNotifications();
    });
});
