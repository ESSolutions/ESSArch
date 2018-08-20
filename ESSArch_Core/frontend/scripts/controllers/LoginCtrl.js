/*
    ESSArch is an open source archiving and digital preservation system

    ESSArch Tools for Archive (ETA)
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
*/

angular.module('myApp').controller('LoginCtrl', function ($scope, $location, $window, myService, $state, $stateParams, $rootScope, djangoAuth, Validate, PermRoleStore, PermPermissionStore){
    $scope.model = {'app': $rootScope.app, 'username':'','password':''};
    $scope.complete = false;
    $scope.login = function(formData){
        $scope.error = null;
        Validate.form_validation(formData,$scope.errors);
        if(!formData.$invalid){
            djangoAuth.login($scope.model.username, $scope.model.password)
                .then(function(data){
                    // success case
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
                    // error case
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
