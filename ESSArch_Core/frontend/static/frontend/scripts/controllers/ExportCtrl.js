export default class ExportCtrl {
  constructor($scope, appConfig, $http, $window, SA, Profile) {
    var vm = this;
    vm.$onInit = function() {
      $http
        .get(appConfig.djangoUrl + 'submission-agreements/', {params: {pager: 'none', published: true}})
        .then(function(response) {
          vm.sas = response.data;
          vm.sa = null;
        });

      $http.get(appConfig.djangoUrl + 'profiles/', {params: {pager: 'none'}}).then(function(response) {
        vm.profiles = response.data;
        vm.profile = null;
      });
    };

    $scope.encodeJson = function(obj) {
      return angular.toJson(obj);
    };

    vm.profileFileName = function(item) {
      if (item) {
        var name = item.name + '.json';
        return name;
      }
    };

    vm.saFileName = function(item) {
      if (item) {
        var name = item.name + '.json';
        return name;
      }
    };
    vm.downloadProfile = function(object) {
      Profile.get({id: object.id}).$promise.then(function(resource) {
        vm.exportToFile($scope.encodeJson(resource), vm.profileFileName(resource));
      });
    };

    vm.downloadSa = function(object) {
      SA.get({id: object.id}).$promise.then(function(resource) {
        vm.exportToFile($scope.encodeJson(resource), vm.saFileName(resource));
      });
    };

    vm.exportToFile = function(object, filename) {
      var blob = new Blob([object], {type: 'text/plain'});
      if ($window.navigator && $window.navigator.msSaveOrOpenBlob) {
        $window.navigator.msSaveOrOpenBlob(blob, filename);
      } else {
        var e = document.createEvent('MouseEvents'),
          a = document.createElement('a');
        a.download = filename;
        a.href = $window.URL.createObjectURL(blob);
        a.dataset.downloadurl = ['text/json', a.download, a.href].join(':');
        e.initEvent('click', true, false, $window, 0, 0, 0, 0, 0, false, false, false, false, 0, null);
        a.dispatchEvent(e);
      }
    };
  }
}
