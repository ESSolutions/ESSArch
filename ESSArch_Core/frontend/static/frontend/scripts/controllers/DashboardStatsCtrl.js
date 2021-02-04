import {isEnabled} from './../features/utils';

export default class DashboardStatsCtrl {
  constructor(appConfig, $http, $uibModal, $log, $translate, $rootScope) {
    const vm = this;
    vm.stats = null;
    vm.chartlabels = [];
    vm.chartoptions = [];
    vm.chartdata = [];
    vm.archivecreatortotal = null;
    vm.$onInit = function () {
      vm.statsLoading = true;
      vm.getStats()
        .then(function (stats) {
          if (isEnabled($rootScope.features, 'archival descriptions')) {
            vm.getAgents(stats)
              .then((statsWithAgents) => {
                vm.stats = statsWithAgents;
                angular.forEach([vm.stats.tags], function (arr) {
                  angular.forEach(arr, function (value) {
                    vm.chartlabels.push(value.type__name);
                    vm.chartdata.push(value.total);
                  });
                });
                vm.chartoptions = {
                  tooltipEvents: [],
                  showTooltips: true,
                  tooltipCaretSize: 0,
                  onAnimationComplete: function () {
                    this.showTooltip(this.segments, true);
                  },
                  legend: {
                    display: true,
                    labels: {
                      fontColor: 'black',
                    },
                  },
                };
                vm.statsLoading = false;
              })
              .catch(() => {
                vm.statsLoading = false;
              });
          } else {
            vm.stats = stats;
            vm.statsLoading = false;
          }
        })
        .catch(() => {
          vm.statsLoading = false;
        });
    };

    vm.getAgents = function (stats) {
      return $http({
        url: appConfig.djangoUrl + 'agents/',
        method: 'HEAD',
      }).then(function (response) {
        vm.archivecreatortotal = response.headers('Count');
        return stats;
      });
    };

    vm.getStats = function () {
      return $http.get(appConfig.djangoUrl + 'stats/').then(function (response) {
        return response.data;
      });
    };

    vm.buildReportModal = function () {
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/modals/stats_report_modal.html',
        controller: 'StatsReportModalInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function () {
            return {
              options: vm.stats,
            };
          },
        },
      });
      modalInstance.result.then(
        function (data) {},
        function () {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
  }
}
