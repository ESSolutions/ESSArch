/* @ngInject */
const loginCtrl = (
  $scope,
  $location,
  $window,
  $http,
  myService,
  $state,
  $stateParams,
  $rootScope,
  djangoAuth,
  Validate,
  PermRoleStore,
  PermPermissionStore,
  appConfig,
  $translate
) => {
  $scope.model = {app: $rootScope.app, username: '', password: ''};
  $scope.complete = false;
  $scope.loggingIn = false;
  $scope.auth_services = [];

  $http({
    method: 'GET',
    url: djangoAuth.API_URL + '/services/',
  }).then(function(response) {
    $scope.auth_services = response.data;
  });

  $scope.login = function(formData) {
    $scope.error = null;
    Validate.form_validation(formData, $scope.errors);
    if (!formData.$invalid) {
      $scope.loggingIn = true;
      djangoAuth
        .login($scope.model.username, $scope.model.password)
        .then(function(data) {
          $scope.loggingIn = false;
          $rootScope.auth = data;
          $rootScope.listViewColumns = myService.generateColumns(data.ip_list_columns).activeColumns;
          PermPermissionStore.clearStore();
          PermRoleStore.clearStore();
          myService.getPermissions(data.permissions);
          if ($stateParams.requestedPage !== '/login') {
            $location.path($stateParams.requestedPage);
            $window.location.reload();
          } else {
            $state.go('home.info');
          }
          $http
            .get(appConfig.djangoUrl + 'site/')
            .then(function(response) {
              $rootScope.site = response.data;
            })
            .catch(function() {
              $rootScope.site = null;
            });
        })
        .catch(function(response) {
          $scope.loggingIn = false;
          if (angular.isUndefined(response.status) && response.data === null) {
            // When server does not respond
            $scope.error = $translate.instant('NO_RESPONSE_FROM_SERVER');
          } else {
            $scope.error = response.data.non_field_errors[0];
          }
        });
    }
  };
};

export default loginCtrl;
