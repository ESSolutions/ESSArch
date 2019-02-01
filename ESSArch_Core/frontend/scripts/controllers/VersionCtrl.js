angular
  .module('essarch.controllers')
  .controller('VersionCtrl', function(
    $scope,
    myService,
    $window,
    $state,
    marked,
    $anchorScroll,
    $location,
    $translate
  ) {
    myService.getVersionInfo().then(function(result) {
      if (result.platform.os == 'Darwin') {
        result.platform.os = 'macOS';
        result.platform.icon = 'fab fa-apple';
        result.platform.version = result.platform.mac_version[0];
      } else if (result.platform.os == 'Windows') {
        result.platform.icon = 'fab fa-windows';
        result.platform.version = result.platform.win_version[0];
      } else {
        result.platform.icon = 'fab fa-linux';
        result.platform.os = result.platform.linux_dist[0];
        result.platform.version = result.platform.linux_dist[1];
      }

      result.python_packages = result.python_packages.map(function(x) {
        return x.split('==');
      });
      $scope.sysInfo = result;
    });
    $scope.redirectToEss = function() {
      $window.open('http://www.essolutions.se', '_blank');
    };
    $scope.scrollToLink = function(link) {
      $location.hash(link);
      $anchorScroll();
    };

    $scope.gotoDocs = function() {
      $window.open('/docs/' + $translate.use() + '/user_guide/index.html', '_blank');
    };

    $scope.tabs = [
      {
        label: $translate.instant('DOCS'),
        templateUrl: 'static/frontend/views/docs.html',
      },
      {
        label: $translate.instant('SYSINFO.SYSTEMINFORMATION'),
        templateUrl: 'sysinfo.html',
      },
      {
        label: $translate.instant('SYSINFO.SUPPORT'),
        templateUrl: 'static/frontend/views/support.html',
      },
    ];
  });
