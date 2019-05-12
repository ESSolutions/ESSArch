angular.module('essarch.services').factory('Appraisal', function($http, appConfig) {
  var service = {};
  service.getFinished = function(pageNumber, pageSize, sortString, searchString) {
    var data = {
      end_date__isnull: false,
      page: pageNumber,
      page_size: pageSize,
      ordering: sortString,
      search: searchString,
    };

    return $http({
      method: 'GET',
      url: appConfig.djangoUrl + 'appraisal-jobs/',
      params: data,
    }).then(function(response) {
      var count = response.headers('Count');
      if (count == null) {
        count = response.data.length;
      }
      return {
        count: count,
        data: response.data,
      };
    });
  };

  service.getNext = function(pageNumber, pageSize, sortString, searchString) {
    var data = {
      status: 'PENDING',
      page: pageNumber,
      page_size: pageSize,
      ordering: sortString,
      search: searchString,
    };

    return $http({
      method: 'GET',
      url: appConfig.djangoUrl + 'appraisal-jobs/',
      params: data,
    }).then(function(response) {
      var count = response.headers('Count');
      if (count == null) {
        count = response.data.length;
      }
      return {
        count: count,
        data: response.data,
      };
    });
  };

  service.getOngoing = function(pageNumber, pageSize, sortString, searchString) {
    var data = {
      status: 'STARTED',
      page: pageNumber,
      page_size: pageSize,
      ordering: sortString,
      search: searchString,
    };

    return $http({
      method: 'GET',
      url: appConfig.djangoUrl + 'appraisal-jobs/',
      params: data,
    }).then(function(response) {
      var count = response.headers('Count');
      if (count == null) {
        count = response.data.length;
      }
      return {
        count: count,
        data: response.data,
      };
    });
  };

  service.getRules = function(pageNumber, pageSize, sortString, searchString) {
    var data = {
      page: pageNumber,
      page_size: pageSize,
      ordering: sortString,
      search: searchString,
    };

    return $http({
      method: 'GET',
      url: appConfig.djangoUrl + 'appraisal-rules/',
      params: data,
    }).then(function(response) {
      var count = response.headers('Count');
      if (count == null) {
        count = response.data.length;
      }
      return {
        count: count,
        data: response.data,
      };
    });
  };
  return service;
});
