import angular from 'angular';

import notificationsComponent from './components/NotificationsComponent';
import notificationsCtrl from './controllers/NotificationsCtrl';
import notificationsService from './services/Notifications';

export default angular
  .module('essarch.notification', [])
  .factory('Notifications', notificationsService)
  .component('notifications', notificationsComponent)
  .controller('NotificationsCtrl', notificationsCtrl).name;
