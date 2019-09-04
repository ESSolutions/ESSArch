const Utils = () => {
  var service = {
    getDiff: function(obja, objb, options) {
      var diff = {};
      for (var key in objb) {
        if (
          typeof objb[key] !== 'object' &&
          objb[key] !== obja[key] &&
          (angular.isUndefined(options.map[key]) || objb[key] !== obja[key][options.map[key]])
        ) {
          diff[key] = objb[key];
        }
      }
      for (var key in obja) {
        if (
          typeof obja[key] !== 'object' &&
          obja[key] !== objb[key] &&
          !diff[key] &&
          (angular.isUndefined(options.map[key]) || obja[key][options.map[key]] !== objb[key])
        ) {
          if (diff[key]) {
            delete diff[key];
          } else {
            diff[key] = null;
          }
        }
      }
      return diff;
    },
  };
  return service;
};

export default Utils;
