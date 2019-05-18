angular
  .module('essarch.controllers')
  .controller('DashboardStatsCtrl', function($scope, appConfig, $http, $uibModal, $log) {
    var vm = this;
    vm.$onInit = function() {
      vm.getStats().then(function(stats) {
        vm.stats = stats;
      });
    };

    vm.getStats = function() {
      return $http.get(appConfig.djangoUrl + 'stats/').then(function(response) {
        return response.data;
      });
    };

    vm.buildReportModal = function() {
      var modalInstance = $uibModal.open({
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
  });
