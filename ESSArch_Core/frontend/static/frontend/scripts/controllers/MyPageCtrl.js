export default class MyPageCtrl {
  constructor($scope, appConfig, $http) {
    const vm = this;
    vm.sites = null;

    vm.$onInit = function () {
      vm.sitesLoading = true;
      vm.getSites()
        .then(function (sites) {
          vm.sites = sites;
          vm.sitesLoading = false;
        })
        .catch(() => {
          vm.sitesLoading = false;
        });
    };
    vm.getSites = function () {
      return $http.get(appConfig.djangoUrl + 'site/').then(function (response) {
        return response.data;
      });
    };
  }
}
