export default class DashboardStatsCtrl {
  constructor(appConfig, $http, $uibModal, $log, $translate) {
    const vm = this;
    vm.stats = null;
    vm.$onInit = function() {
      vm.statsLoading = true;
      vm.getStats()
        .then(function(stats) {
          vm.getAgents(stats)
            .then(statsWithAgents => {
              vm.stats = statsWithAgents;
              vm.statsLoading = false;
            })
            .catch(() => {
              vm.statsLoading = false;
            });
        })
        .catch(() => {
          vm.statsLoading = false;
        });
    };

    vm.getAgents = function(stats) {
      return $http({
        url: appConfig.djangoUrl + 'agents/',
        method: 'HEAD',
        params: {
          pager: 'none',
        },
      }).then(function(response) {
        stats.tags.unshift({type__name: $translate.instant('ARCHIVECREATORS'), total: response.headers('Count')});
        return stats;
      });
    };

    vm.getStats = function() {
      return $http.get(appConfig.djangoUrl + 'stats/').then(function(response) {
        return response.data;
      });
    };

    vm.buildReportModal = function() {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/modals/stats_report_modal.html',
        controller: 'StatsReportModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function() {
            return {
              options: vm.stats,
            };
          },
        },
      });
      modalInstance.result.then(
        function(data) {},
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
  }
}
