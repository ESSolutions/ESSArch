angular.module('essarch.services').factory('Utils', function() {
  var service = {
    getDiff: function(obja, objb) {
      var diff = {};
      for (var key in objb) {
        if((typeof objb[key] !== 'object') && objb[key] !== obja[key]) {
          diff[key] = objb[key];
        }
      }
      for (var key in obja) {
        if((typeof obja[key] !== 'object') && obja[key] !== objb[key] && !diff[key]) {
          diff[key] = null;
        }
      }
      return diff;
    },
  };
  return service;
});
