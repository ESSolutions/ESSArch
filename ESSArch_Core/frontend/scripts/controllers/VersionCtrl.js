angular.module('essarch.controllers').controller('VersionCtrl', function($scope, myService, $window, $state, marked, $anchorScroll, $location, $translate) {
    myService.getVersionInfo().then(function(result) {
        if (result.platform.os == 'Darwin'){
            result.platform.os = 'macOS';
            result.platform.icon = 'fab fa-apple';
            result.platform.version = result.platform.mac_version[0];
        } else if (result.platform.os == 'Windows') {
            result.platform.icon = 'fab fa-windows';
            result.platform.version = result.platform.win_version[0];
        } else {
            result.platform.icon = 'fab fa-linux';
        }

        $scope.sysInfo = result;
    });
    $scope.redirectToEss = function(){
        $window.open('http://www.essolutions.se', '_blank');
    };
    $scope.scrollToLink = function(link) {
        $location.hash(link);
        $anchorScroll();
    }

    $scope.gotoDocs = function() {
        $window.open("/docs/"+$translate.use()+"/user_guide/index.html", '_blank');
    }

    $scope.docs = $translate.instant('DOCS');
    $scope.sysInfo = $translate.instant('SYSTEMINFORMATION');
    $scope.support = $translate.instant('SUPPORT');
    $scope.tabs = [
        {
            label: $scope.docs,
            templateUrl: 'static/frontend/views/docs.html'
        },
        {
            label: $scope.sysInfo,
            templateUrl: "sysinfo.html"
        },
        {
            label: $scope.support,
            templateUrl: "static/frontend/views/support.html"
        }
    ];
});
