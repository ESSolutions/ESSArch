import controller from '../controllers/DashboardStatsCtrl';
export default {
  templateUrl: 'static/frontend/views/dashboard_stats.html',
  controller: ['appConfig', '$http', '$uibModal', '$log', controller],
  controllerAs: 'vm',
  bindings: {},
};
