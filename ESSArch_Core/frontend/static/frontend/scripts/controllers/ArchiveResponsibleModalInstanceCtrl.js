angular
  .module('essarch.controllers')
  .controller('ArchiveResponsibleModalInstanceCtrl', function($uibModalInstance, $timeout, $q) {
    var $ctrl = this;
    $ctrl.archivesLoading = false;

    $ctrl.$onInit = function() {
      $ctrl.refreshArchives();
    };
    $ctrl.refreshArchives = function() {
      $ctrl.archivesLoading = true;
      $ctrl.getArchives($ctrl.responsible).then(function(response) {
        $ctrl.archivesLoading = false;
        $ctrl.archives = response.data;
      });
    };

    $ctrl.options = {
      type: [
        {main_type: 'Pastorat', id: '1'},
        {main_type: 'Församling', id: '2'},
        {main_type: 'Stift', id: '3'},
        {main_type: 'Nationellt organ', id: '4'},
      ],
      units: [],
    };

    $ctrl.responsible = {
      id: null,
      name: null,
      type: null,
    };

    $ctrl.archives = [];

    $ctrl.getUnits = function(search, prop) {
      $ctrl.units({q: search, prop: prop ? prop : null}).then(function(response) {
        $ctrl.options.units = response.data;
      });
    };

    // Mocked data
    $ctrl.units = function(options) {
      var deferred = $q.defer();
      $timeout(function() {
        var list = [
          {name: 'Anders', id: '1'},
          {name: 'Berit', id: '2'},
          {name: 'Pelle', id: '3'},
          {name: 'Stina', id: '4'},
        ];
        var filtered = list;
        if (options && options.q) {
          filtered = list.filter(function(item) {
            return item[options.prop].includes(options.q);
          });
        }
        deferred.resolve({data: filtered});
      }, 600);
      return deferred.promise;
    };

    $ctrl.getArchives = function(responsible) {
      var deferred = $q.defer();
      $timeout(function() {
        var map = {
          '1': [{name: 'arkiv1', reference_code: 'ark1/bla/bla'}, {name: 'arkiv2', reference_code: 'ark2/bla/bla'}],
          '2': [{name: 'arkiv3', reference_code: 'ark3/bla/bla'}, {name: 'arkiv4', reference_code: 'ark4/bla/bla'}],
          '3': [{name: 'arkiv1', reference_code: 'ark1/bla/bla'}, {name: 'arkiv3', reference_code: 'ark3/bla/bla'}],
          '4': [{name: 'arkiv4', reference_code: 'ark4/bla/bla'}, {name: 'arkiv1', reference_code: 'ark1/bla/bla'}],
        };
        var data = map[responsible.id];
        deferred.resolve({
          data: data ? data : [],
        });
      }, 300);
      return deferred.promise;
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  });
