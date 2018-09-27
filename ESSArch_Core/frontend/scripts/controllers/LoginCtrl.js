angular.module('essarch.controllers').controller('LoginCtrl', function ($scope, $location, $window, $http, myService, $state, $stateParams, $rootScope, djangoAuth, Validate, PermRoleStore, PermPermissionStore){
    $scope.model = {'app': $rootScope.app, 'username':'','password':''};
    $scope.complete = false;
    $scope.auth_services = [];

    $http({
        method: 'GET',
        url: '/rest-auth/services/',
    }).then(function(response) {
        $scope.auth_services = response.data;
    });

    $scope.login = function(formData){
        $scope.error = null;
        Validate.form_validation(formData,$scope.errors);
        if(!formData.$invalid){
            djangoAuth.login($scope.model.username, $scope.model.password)
                .then(function(data){
                    $rootScope.auth = data;
                    $rootScope.listViewColumns = myService.generateColumns(data.ip_list_columns).activeColumns;
                    PermPermissionStore.clearStore();
                    PermRoleStore.clearStore();
                    myService.getPermissions(data.permissions);
                    if($stateParams.requestedPage !== '/login') {
                        $location.path($stateParams.requestedPage);
                        $window.location.reload();
                    } else {
                        $state.go('home.info');
                    }
                }).catch(function(response){
                    if(angular.isUndefined(response.status) && response.data === null) {
                        // When server does not respond
                        $scope.error = "No response from server";
                    } else {
                        $scope.error = response.data.non_field_errors[0];
                    }
                });
        }
    }
});
