export default class ActionWorkflowCtrl {
  constructor($scope, $rootScope, appConfig, $translate, $http, $timeout, $uibModal) {
    const vm = this;
    vm.options = {profiles: []};

     vm.getProfiles = function (search) {
      return $http({
        url: appConfig.djangoUrl + 'profiles/?type=action_workflow',
        method: 'GET',
        params: {search: search, pager: 'none'},
      }).then(function (response) {
        vm.options.profiles = response.data.map((profile) => {
          return profile;
        });
        return vm.options.profiles;
      });
    };

    }}

