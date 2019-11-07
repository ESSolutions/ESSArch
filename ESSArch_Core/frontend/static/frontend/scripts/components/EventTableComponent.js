import EventCtrl from '../controllers/EventCtrl';

export default {
  templateUrl: 'static/frontend/views/event_table.html',
  controller: [
    'Resource',
    '$scope',
    '$rootScope',
    'listViewService',
    '$interval',
    'appConfig',
    '$cookies',
    '$window',
    '$translate',
    '$http',
    'Notifications',
    '$transitions',
    'Filters',
    '$timeout',
    '$state',
    EventCtrl,
  ],
  controllerAs: 'vm',
  bindings: {
    ip: '<',
  },
};
